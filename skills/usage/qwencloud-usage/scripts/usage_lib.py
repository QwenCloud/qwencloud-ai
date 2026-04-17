#!/usr/bin/env python3
"""
QwenCloud Usage Library

Core library: authentication, API client, data layer, business logic, formatting.
"""

import logging
import math
import os
import re
import sys
import json
import unicodedata
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Iterator, Optional

log = logging.getLogger(__name__)


# ========== 1. Exceptions ==========

class AuthError(Exception):
    """Authentication error."""
    pass


class APIError(Exception):
    """API call error."""
    pass


# ========== 2. Authentication ==========

# Auth mode for the current session: "cli" (Bearer)
_AUTH_MODE = "cli"


# ═══════════════════════════════════════════════════════════════════════════════
# Device Flow Process Lock
# ═══════════════════════════════════════════════════════════════════════════════

class _DeviceFlowLock:
    """
    Cross-platform exclusive file lock for the Device Flow login phase.

    Prevents multiple concurrent processes from each launching an independent
    Device Flow (which would open multiple browser tabs and leave all but one
    device token permanently pending until expiry).

    Concurrent-process safety strategy:
    - The first process acquires the lock and runs Device Flow.
    - Subsequent processes block on the lock; once released they re-check
      CliCredentialStore. If valid credentials now exist (written by the winner)
      they return immediately without triggering another Device Flow.

    Lock file: ~/.qwencloud/device_flow.lock
    Locking mechanism: fcntl.flock (Unix) / msvcrt byte-range lock (Windows).
    Both are released automatically when the process exits, so there is no
    risk of a stale lock from a crashed process blocking future runs.
    """

    _LOCK_PATH = None  # resolved lazily to avoid Path construction at import time

    def __init__(self, timeout: int = 300):
        self._timeout = timeout
        self._fh = None

    @classmethod
    def _lock_path(cls):
        from pathlib import Path
        if cls._LOCK_PATH is None:
            cls._LOCK_PATH = Path.home() / ".qwencloud" / "device_flow.lock"
        return cls._LOCK_PATH

    def __enter__(self):
        import time
        lock_path = self._lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        self._fh = open(lock_path, "w")

        deadline = time.monotonic() + self._timeout
        first_wait = True

        if os.name == "nt":
            self._acquire_windows(deadline, first_wait)
        else:
            self._acquire_unix(deadline, first_wait)

        return self

    def _acquire_unix(self, deadline: float, first_wait: bool) -> None:
        import fcntl
        import time

        while True:
            try:
                fcntl.flock(self._fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if first_wait:
                    first_wait = False
                    print(
                        "[device-flow] Another process is performing login, waiting ...",
                        file=sys.stderr,
                    )
                if time.monotonic() > deadline:
                    self._fh.close()
                    self._fh = None
                    raise TimeoutError(
                        f"Timed out ({self._timeout}s) waiting for another "
                        "process to complete Device Flow login."
                    )
                time.sleep(2)

    def _acquire_windows(self, deadline: float, first_wait: bool) -> None:
        import msvcrt
        import time

        while True:
            try:
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if first_wait:
                    first_wait = False
                    print(
                        "[device-flow] Another process is performing login, waiting ...",
                        file=sys.stderr,
                    )
                if time.monotonic() > deadline:
                    self._fh.close()
                    self._fh = None
                    raise TimeoutError(
                        f"Timed out ({self._timeout}s) waiting for another "
                        "process to complete Device Flow login."
                    )
                time.sleep(2)

    def __exit__(self, *_):
        if self._fh is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                fcntl.flock(self._fh, fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None


def get_access_token(force_refresh: bool = False, allow_poll: bool = False) -> str:
    """
    Obtain an access token using a layered resolution strategy:

    1. CLI credential store (keyring → ~/.qwencloud/credentials file)
    2. Interactive Device Flow login

    Sets _AUTH_MODE = "cli" (Bearer, no sec_token).
    """
    global _AUTH_MODE

    # ── CLI path: Device Flow mode ─────────────────────────────────────
    from credential_store import get_cli_store
    from device_flow import device_flow_login, is_token_expired, DeviceFlowError

    cli_store = get_cli_store()

    # 1. Fast path: try saved CLI credentials before acquiring any lock
    if not force_refresh:
        creds = cli_store.load()
        if creds and not is_token_expired(creds):
            _AUTH_MODE = "cli"
            return creds["access_token"]

    # 2. Acquire process lock then double-check before launching Device Flow.
    #    Multiple concurrent processes (e.g. parallel Agent tasks) will each
    #    reach this point and contend for the lock.  Only the winner executes
    #    Device Flow; the others wait, then re-read CliCredentialStore — if
    #    the winner already saved credentials the waiters return immediately
    #    without opening an additional browser tab.
    with _DeviceFlowLock(timeout=300):
        # Double-check: another process may have completed login while we waited
        if not force_refresh:
            creds = cli_store.load()
            if creds and not is_token_expired(creds):
                _AUTH_MODE = "cli"
                print(
                    "[device-flow] Login completed by another process, reusing credentials.",
                    file=sys.stderr,
                )
                return creds["access_token"]

        try:
            # Check for a pending headless session before starting a new flow.
            # This handles the case where the user ran "login --headless" and
            # then directly ran "summary" without an explicit "--poll" step.
            from device_flow import (
                load_pending_session as _load_pending,
                device_flow_poll as _df_poll,
                device_flow_start as _df_start,
                is_headless_mode as _is_headless,
            )
            pending = _load_pending()
            if pending:
                url = pending.get("verification_url", "")
                if allow_poll:
                    # Phase 2: agent explicitly requested poll via --poll
                    if url:
                        print(
                            f"\n[device-flow] Polling for authorization ...\n"
                            f"  URL: {url}\n",
                            file=sys.stderr,
                        )
                    creds = _df_poll()
                else:
                    # Phase 1: show URL to user, agent must immediately --poll
                    print(
                        f"\n[device-flow] Pending login found.\n"
                        f"\n  {url}\n"
                        f"\n  ```markdown\n[Authorize in QwenCloud]({url})\n```\n"
                        f"\n[device-flow] ACTION REQUIRED: Present the above URL to the user, "
                        f"then IMMEDIATELY re-run this exact command with --poll appended.\n",
                        file=sys.stderr,
                    )
                    raise AuthError(
                        f"[HEADLESS_LOGIN_ACTION] "
                        f"url={url} | "
                        f"markdown=[Authorize in QwenCloud]({url}) | "
                        f"action=Present URL to user then IMMEDIATELY re-run with --poll"
                    )
            elif _is_headless():
                session = _df_start()
                url = session["verification_url"]
                print(
                    f"\n[device-flow] Headless login: open this URL to sign in:\n"
                    f"\n  {url}\n"
                    f"\n  ```markdown\n[Authorize in QwenCloud]({url})\n```\n"
                    f"\n[device-flow] ACTION REQUIRED: Present the above URL to the user, "
                    f"then IMMEDIATELY re-run this exact command with --poll appended.\n",
                    file=sys.stderr,
                )
                raise AuthError(
                    f"[HEADLESS_LOGIN_ACTION] "
                    f"url={url} | "
                    f"markdown=[Authorize in QwenCloud]({url}) | "
                    f"action=Present URL to user then IMMEDIATELY re-run with --poll"
                )
            else:
                creds = device_flow_login()
        except DeviceFlowError as e:
            raise AuthError(f"Device Flow login failed: {e}")
        cli_store.save(creds)
        _AUTH_MODE = "cli"
        return creds["access_token"]


def _invalidate_cached_token():
    """Clear persisted CLI credential caches."""
    try:
        from credential_store import get_cli_store
        get_cli_store().clear()
    except Exception as e:
        log.warning("Failed to clear cached credentials: %s", e)


def run_logout(args) -> None:
    """
    Revoke the current session server-side, then clear all local credentials.

    Calls POST https://t.qwencloud.com/cli/device/logout?token=<auth_token>
    (token query param is optional).  Uses Authorization: Bearer <access_token>.

    The server-side call is best-effort: a network failure does NOT prevent
    local credential removal, so the user is always logged out locally.
    """
    from credential_store import get_cli_store

    cli_store = get_cli_store()
    creds = cli_store.load()
    access_token = creds.get("access_token") if creds else None

    if access_token:
        base_url = "https://t.qwencloud.com/cli/device/logout"
        token_param = getattr(args, "token", None)
        url = f"{base_url}?token={urllib.parse.quote(token_param)}" if token_param else base_url
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(
                f"Warning: server-side session revocation failed: {e}. "
                "Local credentials will still be cleared.",
                file=sys.stderr,
            )

    # ── Local credential cleanup (unconditional) ─────────────────────
    try:
        cli_store.clear()
    except Exception:
        pass

    try:
        from device_flow import _clear_pending_session
        _clear_pending_session()
    except Exception:
        pass

    print("Logged out.", file=sys.stderr)


# ========== 3. API client ==========

def _flatten_params(params: dict) -> dict:
    """
    Flatten a params dict to Map<String, String> for the v2 API.

    The /data/v2/api.json endpoint requires every value in the params map to
    be a string.  Scalars (bool, int, float) are stringified; dicts and lists
    are JSON-serialized; strings are kept as-is.
    """
    flat: dict = {}
    for k, v in params.items():
        if isinstance(v, str):
            flat[k] = v
        elif isinstance(v, bool):
            flat[k] = json.dumps(v)            # True → "true"
        elif isinstance(v, (int, float)):
            flat[k] = str(v)
        elif isinstance(v, (dict, list)):
            flat[k] = json.dumps(v)
        else:
            flat[k] = str(v)
    return flat


class QwenCloudAPI:
    """QwenCloud API client."""

    def __init__(
        self,
        access_token: str,
    ):
        """
        Args:
            access_token: Bearer access token for CLI mode.
        """
        self.access_token = access_token
        self.base_url = "https://cli.qwencloud.com"
        self.coding_plan_url = "https://cli.qwencloud.com"

    def _build_form_data(self, product: str, action: str, params: Optional[dict] = None) -> dict:
        """Build JSON body for POST requests.

        ``params`` is stored as a flattened dict (Map<String, String>).
        """
        data = {
            "product": product,
            "action": action,
            "region": "ap-southeast-1",
        }
        if params:
            data["params"] = _flatten_params(params)
        return data

    def _request(self, url: str, form_data: dict) -> dict:
        """
        Send a POST request with JSON body and Authorization: Bearer header.

        Args:
            url: Target URL.
            form_data: Request payload (serialized as JSON).

        Returns:
            dict: API response ``data`` field.

        Raises:
            APIError: on HTTP / network / parsing errors.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        encoded_data = json.dumps(form_data).encode("utf-8")

        req = urllib.request.Request(url, data=encoded_data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw_content = response.read().decode('utf-8')

                if raw_content.strip().startswith('<!DOCTYPE') or raw_content.strip().startswith('<html'):
                    raise APIError(
                        f"Received HTML response instead of JSON from {url}. "
                        "This usually means authentication expired or API endpoint changed."
                    )

                data = json.loads(raw_content)

                if data.get("code") != "200":
                    raise APIError(f"API error: {data.get('message', 'Unknown')}")

                return data.get("data", {})
        except urllib.error.HTTPError as e:
            raise APIError(f"HTTP error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise APIError(f"Network error: {e.reason}")

    def request_home(self, product: str, action: str, params: Optional[dict] = None) -> dict:
        """
        Call the main site API.

        Args:
            product: Product identifier.
            action: API action name.
            params: Optional business parameters.

        Returns:
            Parsed ``data`` field from the API response.
        """
        url = f"{self.base_url}/data/v2/api.json"
        form_data = self._build_form_data(product, action, params)
        return self._request(url, form_data)

    def request_data(self, api: str, data: Optional[dict] = None) -> dict:
        """
        Call the data analytics gateway API.

        Args:
            api: API path (e.g. zeldaEasy.broadscope-bailian.codingPlan.queryCodingPlanInstanceInfoV2).
            data: Payload wrapped in the Data field where applicable.

        Returns:
            Parsed ``data`` field from the API response.
        """
        if "codingPlan" in api:
            url = f"{self.coding_plan_url}/data/v2/api.json"
            data_payload = data if data else {}
            coding_plan_host = self.coding_plan_url.removeprefix("https://").removeprefix("http://")
            data_payload["cornerstoneParam"] = {
                "domain": coding_plan_host,
                "consoleSite": "QWENCLOUD",
                "console": "ONE_CONSOLE",
                "xsp_lang": "en-US",
                "protocol": "V2",
                "productCode": "p_efm"
            }
            form_data = {
                "product": "sfm_bailian",
                "action": "IntlBroadScopeAspnGateway",
                "params": _flatten_params({
                    "Api": api,
                    "Data": data_payload,
                    "V": "1.0",
                }),
                "region": "ap-southeast-1",
            }
        else:
            url = f"{self.base_url}/data/v2/api.json"
            form_data = {
                "product": "sfm_bailian",
                "action": "IntlBroadScopeAspnGateway",
                "api": api,
                "region": "ap-southeast-1",
            }
            if data:
                form_data["Data"] = data

        return self._request(url, form_data)


# ========== 4. Data layer ==========

# Line item categories to skip (not model usage): rounding, refunds, credits.
_SKIP_LINE_ITEM_CATEGORIES = frozenset([
    "Rounding Adjustment",
    "Refund",
    "Credit Adjustment",
])


def _parse_billing_item(
    item: dict,
    *,
    cost_mode: str = "full",
) -> Optional[dict]:
    """
    Parse and normalize a single MaasListConsumeSummary line item.

    Applies _SKIP_LINE_ITEM_CATEGORIES skip rules; free-tier lines are kept
    with ``is_free=True``. Extracts standard fields. Returns None for items
    that should be skipped entirely.

    Args:
        item: Raw line item from the API.
        cost_mode: ``full`` uses RequireAmount, Amount, Cost, ListPrice;
            ``minimal`` uses only RequireAmount and ListPrice (daily/monthly aggregates).

    Returns:
        Normalized dict with keys: line_item_cat, billing_date, billing_month,
        model_id, usage_value, cost, billing_unit, is_free; or None if skipped.
    """
    line_item_cat = item.get("LineItemCategory", "")
    if line_item_cat in _SKIP_LINE_ITEM_CATEGORIES:
        return None

    is_free = "Free" in line_item_cat

    bill_quantity = float(item.get("BillQuantity", 0))
    step_unit = item.get("StepQuantityUnit", "")
    billing_item_code = item.get("BillingItemCode", "")

    billing_unit = infer_billing_unit(step_unit, billing_item_code)
    usage_value = compute_usage_value(bill_quantity, step_unit) if step_unit else bill_quantity

    if cost_mode == "minimal":
        cost = float(item.get("RequireAmount") or item.get("ListPrice") or 0)
    else:
        cost = float(
            item.get("RequireAmount")
            or item.get("Amount")
            or item.get("Cost")
            or item.get("ListPrice")
            or 0
        )

    billing_date = item.get("BillingDate", "")
    billing_month = item.get("BillingMonth") or (billing_date[:7] if billing_date else "")

    model_id = item.get("ModelName") or item.get("Model") or ""

    return {
        "line_item_cat": line_item_cat,
        "billing_date": billing_date,
        "billing_month": billing_month,
        "model_id": model_id,
        "usage_value": usage_value,
        "cost": cost,
        "billing_unit": billing_unit,
        "is_free": is_free,
    }


def _iter_parsed_billing_items(
    items: list,
    *,
    cost_mode: str = "full",
) -> Iterator[dict]:
    """Yield normalized billing rows, skipping categories in _SKIP_LINE_ITEM_CATEGORIES."""
    for item in items:
        row = _parse_billing_item(item, cost_mode=cost_mode)
        if row is not None:
            yield row


def fetch_free_tier(api: QwenCloudAPI) -> list:
    """
    Fetch Free Tier quota information.

    Args:
        api: API client instance.

    Returns:
        List of dicts with model_id and quota details.
    """
    try:
        data = api.request_home("BssOpenAPI-V3", "DescribeFqInstance", params={"PageSize": 1000})
    except (APIError, Exception) as e:
        log.warning("Failed to fetch free tier data: %s", e)
        return []

    free_tier_list = []
    for item in data.get("Data", []):
        try:
            template = item.get("Template", {})
            model_name = template.get("Name", "Unknown")

            init_capacity = item.get("InitCapacity", {})
            curr_capacity = item.get("CurrCapacity", {})

            show_unit = init_capacity.get("ShowUnit", "Tokens")
            base_value = init_capacity.get("BaseValue", 0)
            curr_value = curr_capacity.get("BaseValue", 0)

            if base_value > 0:
                used_pct = int((base_value - curr_value) / base_value * 100)
            else:
                used_pct = 0

            unit = "tokens"
            if "Image" in show_unit:
                unit = "images"
            elif "Character" in show_unit:
                unit = "characters"
            elif "Second" in show_unit:
                unit = "seconds"

            free_tier_list.append({
                "model_id": model_name,
                "quota": {
                    "remaining": curr_value,
                    "total": base_value,
                    "unit": unit,
                    "used_pct": used_pct
                }
            })
        except (KeyError, TypeError, ValueError) as e:
            log.warning("Skipping malformed free tier item: %s", e)
            continue

    return free_tier_list


def fetch_coding_plan(api: QwenCloudAPI) -> dict:
    """
    Fetch Coding Plan subscription and quota windows.

    Args:
        api: API client instance.

    Returns:
        Dict with subscribed, plan, windows, etc.
    """
    try:
        request_data = {
            "queryCodingPlanInstanceInfoRequest": {
                "commodityCode": "sfm_codingplan_public_intl",
                "onlyLatestOne": True
            }
        }
        data = api.request_data(
            "zeldaEasy.broadscope-bailian.codingPlan.queryCodingPlanInstanceInfoV2",
            request_data
        )

        coding_plan_data = data.get("DataV2", {}).get("data", {}).get("data", {})
        instances = coding_plan_data.get("codingPlanInstanceInfos", [])

        if not instances:
            return {"subscribed": False}

        instance = instances[0]
        quota_info = instance.get("codingPlanQuotaInfo", {})

        if instance.get("status") != "VALID":
            return {"subscribed": False}

        windows = {
            "per_5h": {
                "remaining": quota_info.get("per5HourTotalQuota", 0) - quota_info.get("per5HourUsedQuota", 0),
                "total": quota_info.get("per5HourTotalQuota", 0),
                "used_pct": int(quota_info.get("per5HourUsedQuota", 0) / max(quota_info.get("per5HourTotalQuota", 1), 1) * 100)
            },
            "weekly": {
                "remaining": quota_info.get("perWeekTotalQuota", 0) - quota_info.get("perWeekUsedQuota", 0),
                "total": quota_info.get("perWeekTotalQuota", 0),
                "used_pct": int(quota_info.get("perWeekUsedQuota", 0) / max(quota_info.get("perWeekTotalQuota", 1), 1) * 100)
            },
            "monthly": {
                "remaining": quota_info.get("perBillMonthTotalQuota", 0) - quota_info.get("perBillMonthUsedQuota", 0),
                "total": quota_info.get("perBillMonthTotalQuota", 0),
                "used_pct": int(quota_info.get("perBillMonthUsedQuota", 0) / max(quota_info.get("perBillMonthTotalQuota", 1), 1) * 100)
            }
        }

        return {
            "subscribed": True,
            "plan": instance.get("instanceType", "unknown"),
            "windows": windows
        }
    except (APIError, json.JSONDecodeError, KeyError, TypeError):
        return {"subscribed": False}


def fetch_payg(api: QwenCloudAPI, from_date: str, to_date: str, models: Optional[list] = None) -> dict:
    """
    Fetch pay-as-you-go usage for a date range.

    Args:
        api: API client instance.
        from_date: Start date (YYYY-MM-DD).
        to_date: End date (YYYY-MM-DD).
        models: Optional list of model IDs to filter; None means all models.

    Returns:
        Dict with per-model usage, cost, and totals.
    """
    import random
    import time

    models_dict = {}
    total_cost = 0.0
    current_page = 1
    max_results = 100
    max_pages = 100

    while current_page <= max_pages:
        params = {
            "Console": True,
            "Granularity": "DAILY",
            "ChargeTypes": ["postpaid"],
            "StartBillingDate": from_date,
            "EndBillingDate": to_date,
            "MaxResults": max_results,
            "CurrentPage": current_page,
        }

        if models:
            params["ModelNames"] = models

        data = api.request_home("BssOpenAPI-V3", "MaasListConsumeSummary", params)

        items = data.get("Data", [])

        for row in _iter_parsed_billing_items(items, cost_mode="full"):
            if row["is_free"]:
                continue

            model_id = row["model_id"]
            if not model_id:
                continue

            amount = row["cost"]
            usage_value = row["usage_value"]

            if model_id not in models_dict:
                models_dict[model_id] = {
                    "model_id": model_id,
                    "usage": _new_unit_bucket(),
                    "cost": 0.0,
                    "currency": "USD"
                }

            unit = row["billing_unit"]
            models_dict[model_id]["usage"][unit] += usage_value
            models_dict[model_id]["cost"] += amount

            total_cost += amount

        if len(items) < max_results:
            break
        current_page += 1
        if current_page <= max_pages:
            time.sleep(random.uniform(0.5, 1.0))

    model_list = []
    for m in models_dict.values():
        m["billing_units"] = _units_present(m["usage"])
        m["usage"] = _bucket_to_usage(m["usage"])
        model_list.append(m)

    return {
        "models": model_list,
        "total": {
            "cost": round(total_cost, 10),
            "currency": "USD"
        }
    }


def infer_billing_unit(step_unit: str, billing_item_code: str = "") -> str:
    """
    Infer billing_unit from MaasListConsumeSummary fields.

    Prefer BillingItemCode when present:
        image_number → images; video_duration → seconds; token_number → tokens;
        char_number → characters.

    Fallback to StepQuantityUnit strings such as 1K tokens, Page, seconds, etc.

    Returns:
        One of: "tokens", "images", "seconds", "characters".
    """
    code = billing_item_code.lower()
    if "image" in code:
        return "images"
    if "video" in code or "duration" in code:
        return "seconds"
    if "char" in code:
        return "characters"
    if "token" in code:
        return "tokens"

    unit_lower = step_unit.lower()
    if "token" in unit_lower:
        return "tokens"
    if "image" in unit_lower or "page" in unit_lower:
        return "images"
    if "second" in unit_lower or "sec" in unit_lower:
        return "seconds"
    if "char" in unit_lower:
        return "characters"
    return "tokens"


def compute_usage_value(bill_quantity: float, step_unit: str) -> float:
    """
    Convert BillQuantity × StepQuantityUnit step size to raw units
    (tokens, images, seconds, characters).

    Examples: 1K tokens → ×1000; 1M tokens → ×1_000_000; Page or seconds with
    no numeric prefix → multiplier 1 (BillQuantity is already in target units).
    """
    m = re.match(r"(\d+(?:\.\d+)?)\s*([kmKM]?)", step_unit.strip())
    if m:
        multiplier_val = float(m.group(1))
        suffix = m.group(2).upper()
        if suffix == "K":
            multiplier_val *= 1_000
        elif suffix == "M":
            multiplier_val *= 1_000_000
        return bill_quantity * multiplier_val
    return bill_quantity


def _new_unit_bucket() -> dict:
    """Empty per-unit accumulator for multi-unit aggregation.

    Returns a defaultdict(float) so that unknown billing units are
    automatically initialised to 0.0 on first access instead of raising
    KeyError.
    """
    return defaultdict(float, {"tokens": 0.0, "images": 0.0, "seconds": 0.0, "characters": 0.0})


# Mapping from bucket key -> usage-dict key for known units.
_KNOWN_UNIT_USAGE_KEYS = {
    "tokens": "tokens_total",
    "images": "images",
    "seconds": "seconds",
    "characters": "characters",
}


def _bucket_to_usage(by_unit: dict) -> dict:
    """Convert per-unit bucket to a usage object, omitting zero-value keys.

    Supports both known and unknown billing units.  Unknown units use their
    bucket key directly as the usage key.
    """
    usage: dict = {}
    for unit_key, val in by_unit.items():
        if val:
            usage_key = _KNOWN_UNIT_USAGE_KEYS.get(unit_key, unit_key)
            usage[usage_key] = val
    return usage or {"tokens_total": 0}


def _units_present(by_unit: dict) -> list:
    """Return sorted list of units that have non-zero values."""
    return sorted(u for u, v in by_unit.items() if v)


def _build_period_rows(by_key: dict) -> list:
    """
    Convert an aggregation dict {period_key: {by_unit, cost}} into sorted
    output rows with backward-compatible single-unit shorthand.
    """
    rows = []
    all_units: set = set()
    for key in sorted(by_key.keys()):
        d = by_key[key]
        units = _units_present(d["by_unit"])
        all_units.update(units)
        rows.append({
            "period": key,
            "usage": _bucket_to_usage(d["by_unit"]),
            "cost": round(d["cost"], 6),
            "currency": "USD",
            "billing_units": units,
        })

    all_units_list = sorted(all_units) or ["tokens"]
    if len(all_units_list) == 1:
        for r in rows:
            r["billing_unit"] = all_units_list[0]

    return rows


def _fetch_payg_by_period(
    api: "QwenCloudAPI",
    from_date: str,
    to_date: str,
    granularity: str,
    models: Optional[list] = None,
) -> list:
    """
    Fetch pay-as-you-go usage aggregated by the requested granularity.

    The API requires date ranges within a single calendar month, so
    cross-month ranges are split via split_into_months().

    Args:
        api:         API client instance.
        from_date:   start date YYYY-MM-DD (inclusive).
        to_date:     end date   YYYY-MM-DD (inclusive).
        granularity: ``"DAILY"`` or ``"MONTHLY"``.
        models:      optional model ID filter (None = all models).

    Returns:
        Sorted list of period rows with multi-unit usage.
    """
    import random
    import time

    by_key: dict = {}
    max_results = 100
    max_pages = 100

    for (month_start, month_end) in split_into_months(from_date, to_date):
        current_page = 1

        while current_page <= max_pages:
            params: dict = {
                "Console": True,
                "Granularity": granularity,
                "ChargeTypes": ["postpaid"],
                "MaxResults": max_results,
                "CurrentPage": current_page,
            }
            if granularity == "DAILY":
                params["StartBillingDate"] = month_start
                params["EndBillingDate"] = month_end
                params["SortName"] = "BillingDate"
                params["SortOrder"] = "DESC"
            else:
                params["BillingMonth"] = month_start[:7]

            if models:
                params["ModelNames"] = models

            data = api.request_home("BssOpenAPI-V3", "MaasListConsumeSummary", params)

            items = data.get("Data", [])

            for row in _iter_parsed_billing_items(
                items, cost_mode="minimal"
            ):
                if granularity == "DAILY":
                    key = row["billing_date"]
                else:
                    key = row["billing_month"] or (
                        row["billing_date"][:7] if row["billing_date"] else ""
                    )
                if not key:
                    continue

                if key not in by_key:
                    by_key[key] = {"by_unit": _new_unit_bucket(), "cost": 0.0}

                if not row["is_free"]:
                    by_key[key]["by_unit"][row["billing_unit"]] += row["usage_value"]
                    by_key[key]["cost"] += row["cost"]

            if len(items) < max_results:
                break
            current_page += 1
            if current_page <= max_pages:
                time.sleep(random.uniform(0.5, 1.0))

    return _build_period_rows(by_key)


def fetch_payg_daily(
    api: "QwenCloudAPI", from_date: str, to_date: str, models: Optional[list] = None
) -> list:
    """Fetch pay-as-you-go usage aggregated by calendar day."""
    return _fetch_payg_by_period(api, from_date, to_date, "DAILY", models)


def fetch_payg_monthly(
    api: "QwenCloudAPI", from_date: str, to_date: str, models: Optional[list] = None
) -> list:
    """Fetch pay-as-you-go usage aggregated by calendar month."""
    return _fetch_payg_by_period(api, from_date, to_date, "MONTHLY", models)


def fetch_payg_quarterly(
    api: "QwenCloudAPI", from_date: str, to_date: str, models: Optional[list] = None
) -> list:
    """
    Aggregate pay-as-you-go usage by calendar quarter (YYYY-QN).

    Reuses fetch_payg_monthly and merges months client-side.
    """
    monthly_rows = fetch_payg_monthly(api, from_date, to_date, models=models)

    by_quarter: dict = {}

    for row in monthly_rows:
        month_str = row["period"]
        try:
            year = int(month_str[:4])
            month_num = int(month_str[5:7])
        except (ValueError, IndexError):
            continue
        quarter = (month_num - 1) // 3 + 1
        quarter_key = f"{year}-Q{quarter}"

        if quarter_key not in by_quarter:
            by_quarter[quarter_key] = {
                "by_unit": _new_unit_bucket(),
                "cost": 0.0,
            }

        usage_obj = row.get("usage", {})
        for unit_key, usage_key in (
            ("tokens", "tokens_total"),
            ("images", "images"),
            ("seconds", "seconds"),
            ("characters", "characters"),
        ):
            by_quarter[quarter_key]["by_unit"][unit_key] += float(usage_obj.get(usage_key, 0))
        by_quarter[quarter_key]["cost"] += row.get("cost", 0.0)

    return _build_period_rows(by_quarter)


# ========== 5. Business logic ==========

def _month_last_day(dt: "datetime") -> "datetime":
    """Return the last day of the month containing dt."""
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1, day=1) - timedelta(days=1)
    return dt.replace(month=dt.month + 1, day=1) - timedelta(days=1)


def split_into_months(from_date: str, to_date: str) -> list:
    """
    Split [from_date, to_date] into per-calendar-month sub-ranges.

    Each tuple is (range_start, range_end) clipped to the original from/to bounds.
    Used so every API call stays within a single calendar month.

    Examples:
        "2026-03-15" ~ "2026-04-12"
          -> [("2026-03-15", "2026-03-31"), ("2026-04-01", "2026-04-12")]
        "2026-03-01" ~ "2026-03-31"
          -> [("2026-03-01", "2026-03-31")]

    Args:
        from_date: YYYY-MM-DD start (inclusive)
        to_date:   YYYY-MM-DD end   (inclusive)

    Returns:
        list of (start, end) YYYY-MM-DD string tuples, one per calendar month
    """
    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")

    ranges = []
    cur = start
    while cur <= end:
        month_end = _month_last_day(cur)
        range_end = min(month_end, end)
        ranges.append((cur.strftime("%Y-%m-%d"), range_end.strftime("%Y-%m-%d")))
        cur = month_end + timedelta(days=1)

    return ranges


def parse_date_period(period_str: str) -> tuple:
    """
    Resolve a preset period string to (from_date, to_date) as YYYY-MM-DD.

    Args:
        period_str: Preset name (month, last-month, week, yesterday, today, etc.)

    Returns:
        (from_date, to_date) strings.
    """
    today = datetime.now()

    if period_str == "today":
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period_str == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")
    elif period_str == "week":
        from_date = today - timedelta(days=7)
        return from_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period_str == "month":
        from_date = today.replace(day=1)
        return from_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period_str == "last-month":
        first_day_this_month = today.replace(day=1)
        last_month_end = first_day_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start.strftime("%Y-%m-%d"), last_month_end.strftime("%Y-%m-%d")
    elif period_str == "quarter":
        quarter = (today.month - 1) // 3 + 1
        first_month_of_quarter = (quarter - 1) * 3 + 1
        from_date = today.replace(month=first_month_of_quarter, day=1)
        return from_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif period_str == "year":
        from_date = today.replace(month=1, day=1)
        return from_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif len(period_str) == 7 and period_str[4] == '-':
        from_date = datetime.strptime(period_str, "%Y-%m")
        if from_date.month == 12:
            to_date = from_date.replace(year=from_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            to_date = from_date.replace(month=from_date.month + 1, day=1) - timedelta(days=1)
        return from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")
    else:
        raise ValueError(f"Invalid period: {period_str}")


def _resolve_date_range(args) -> tuple:
    """
    Resolve CLI date arguments into (from_date, to_date) strings.

    Handles ``--from/--to``, ``--days``, ``--period``, and the default (current month).
    """
    if args.from_date and args.to_date:
        return args.from_date, args.to_date
    if hasattr(args, "days") and args.days:
        return (
            (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
        )
    return parse_date_period(args.period or "month")


def _build_api_client(args, force_refresh: bool = False) -> "QwenCloudAPI":
    """Authenticate and return a ready-to-use API client."""
    allow_poll = getattr(args, "poll", False)
    access_token = get_access_token(
        force_refresh=force_refresh, allow_poll=allow_poll,
    )
    return QwenCloudAPI(access_token)


def run_summary(args, force_refresh: bool = False) -> dict:
    """
    Run the usage summary command and return structured data.

    Args:
        args: Parsed CLI arguments.
        force_refresh: If True, bypass access_token cache.

    Returns:
        Summary dict (period, free_tier, coding_plan, pay_as_you_go).
    """
    from_date, to_date = _resolve_date_range(args)
    api = _build_api_client(args, force_refresh)

    free_tier = fetch_free_tier(api)
    coding_plan = fetch_coding_plan(api)
    payg = fetch_payg(api, from_date, to_date)

    return {
        "period": {"from": from_date, "to": to_date},
        "free_tier": free_tier,
        "coding_plan": coding_plan,
        "pay_as_you_go": payg
    }


def run_breakdown(args, force_refresh: bool = False) -> dict:
    """
    Run the usage breakdown command and return structured data.

    Args:
        args: Parsed CLI arguments.
        force_refresh: If True, bypass access_token cache.

    Returns:
        Breakdown dict (model_id, billing_unit, period, rows, total, ...).
    """
    from_date, to_date = _resolve_date_range(args)
    api = _build_api_client(args, force_refresh)

    granularity = getattr(args, 'granularity', 'day')

    model_filter = args.model

    if granularity == "day":
        rows = fetch_payg_daily(api, from_date, to_date, models=model_filter)
        display_from, display_to = from_date, to_date
    elif granularity == "month":
        rows = fetch_payg_monthly(api, from_date, to_date, models=model_filter)
        month_ranges = split_into_months(from_date, to_date)
        display_from = month_ranges[0][0] if month_ranges else from_date
        display_to = month_ranges[-1][1] if month_ranges else to_date
    else:
        rows = fetch_payg_quarterly(api, from_date, to_date, models=model_filter)
        month_ranges = split_into_months(from_date, to_date)
        display_from = month_ranges[0][0] if month_ranges else from_date
        display_to = month_ranges[-1][1] if month_ranges else to_date

    # Collect all units across rows
    all_units: set = set()
    for r in rows:
        all_units.update(r.get("billing_units", []))
        if "billing_unit" in r:
            all_units.add(r["billing_unit"])
    billing_units = sorted(all_units) or ["tokens"]

    # Build total usage across all units
    total_cost = sum(r.get("cost", 0) for r in rows)
    total_by_unit = _new_unit_bucket()
    for r in rows:
        usage = r.get("usage", {})
        for unit_key, usage_key in (
            ("tokens", "tokens_total"),
            ("images", "images"),
            ("seconds", "seconds"),
            ("characters", "characters"),
        ):
            total_by_unit[unit_key] += float(usage.get(usage_key, 0))

    result = {
        "model_id": ",".join(model_filter) if model_filter else "all",
        "billing_units": billing_units,
        "period": {"from": display_from, "to": display_to},
        "granularity": granularity,
        "rows": rows,
        "total": {
            "usage": _bucket_to_usage(total_by_unit),
            "cost": round(total_cost, 10),
            "currency": "USD",
        }
    }

    # Backward-compat: single-unit shorthand
    if len(billing_units) == 1:
        result["billing_unit"] = billing_units[0]

    return result


# ========== 6. Formatting ==========

def format_number(num: int) -> str:
    """
    Compact number formatting (1000 → 1K, 1000000 → 1M).

    Args:
        num: Integer or numeric value to format.

    Returns:
        Short string representation.
    """
    if num >= 1000000:
        return f"{num / 1000000:.1f}M".rstrip('0').rstrip('.')
    elif num >= 1000:
        return f"{num / 1000:.1f}K".rstrip('0').rstrip('.')
    else:
        return str(num)


def format_cost(cost: float) -> str:
    """
    Format a currency string with precision suited to the magnitude.

    - |value| >= 0.01: two decimal places (e.g. $1.23)
    - Non-zero |value| < 0.01: up to 10 significant-style decimals so it is not $0.00
    - Zero: $0.00
    """
    if cost == 0:
        return "$0.00"
    abs_cost = abs(cost)
    if abs_cost >= 0.01:
        return f"${cost:.2f}"
    digits = max(2, -int(math.floor(math.log10(abs_cost))) + 1)
    digits = min(digits, 10)
    return f"${cost:.{digits}f}"


def format_progress_bar(percentage: int, max_width: int = 20) -> str:
    """
    Build a simple ASCII progress bar.

    Args:
        percentage: Value from 0 to 100.
        max_width: Bar width in characters.

    Returns:
        Bar string using filled and empty block characters.
    """
    filled = int(percentage / 100 * max_width)
    empty = max_width - filled
    return "█" * filled + "░" * empty


def calc_display_width(text: str) -> int:
    """
    Display width of a string for terminal alignment (East Asian width aware).

    Args:
        text: Input string.

    Returns:
        Column width (wide chars count as 2).
    """
    width = 0
    for char in text:
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('F', 'W'):
            width += 2
        else:
            width += 1
    return width


def pad_right(text: str, width: int) -> str:
    """
    Pad a string with spaces on the right to reach a target display width.

    Args:
        text: Cell text.
        width: Target display width.

    Returns:
        Padded string.
    """
    current_width = calc_display_width(text)
    padding_needed = width - current_width
    if padding_needed > 0:
        return text + " " * padding_needed
    return text


def format_json(data: dict) -> str:
    """Serialize data as indented JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def _format_free_tier_section(free_tier: list) -> list[str]:
    """
    Build TTY lines for the Free Tier quota table.

    Args:
        free_tier: List of free-tier model entries from the summary payload.

    Returns:
        List of strings (no trailing blank line).
    """
    lines = []
    if free_tier:
        row_data = []
        for item in free_tier:
            model_id = item.get("model_id", "Unknown")
            quota = item.get("quota", {})
            if quota:
                remaining = format_number(quota.get("remaining", 0))
                total = format_number(quota.get("total", 0))
                unit = quota.get("unit", "tokens")
                used_pct = quota.get("used_pct", 0)
                remaining_pct = 100 - used_pct
                progress = format_progress_bar(remaining_pct, 15)
                progress_col = f"[{progress}] {remaining_pct}% left"
                row_data.append({
                    "model_id": model_id,
                    "remaining": f"{remaining} {unit}",
                    "total": f"{total} {unit}",
                    "progress": progress_col
                })
            else:
                early_access = "Free (Early Access)"
                row_data.append({
                    "model_id": model_id,
                    "remaining": "—",
                    "total": "—",
                    "progress": early_access
                })

        col0_width = max(calc_display_width(r["model_id"]) for r in row_data)
        col1_width = max(calc_display_width(r["remaining"]) for r in row_data)
        col2_width = max(calc_display_width(r["total"]) for r in row_data)
        col3_width = max(calc_display_width(r["progress"]) for r in row_data)

        col0_width = max(col0_width, calc_display_width("Model"))
        col1_width = max(col1_width, calc_display_width("Remaining"))
        col2_width = max(col2_width, calc_display_width("Total"))
        col3_width = max(col3_width, calc_display_width("Progress"))

        table_width = col0_width + 1 + col1_width + 1 + col2_width + 1 + col3_width

        title_text = "-- Free Tier Quota "
        title_padding = max(0, table_width - calc_display_width(title_text))
        lines.append(title_text + "-" * title_padding)

        header = f"{pad_right('Model', col0_width)} {pad_right('Remaining', col1_width)} {pad_right('Total', col2_width)} {pad_right('Progress', col3_width)}"
        lines.append(header)
        lines.append("-" * table_width)

        for r in row_data:
            row = f"{pad_right(r['model_id'], col0_width)} {pad_right(r['remaining'], col1_width)} {pad_right(r['total'], col2_width)} {r['progress']}"
            lines.append(row)
    else:
        lines.append("No free tier quota available for this account.")
    return lines


def _format_coding_plan_section(coding_plan: dict) -> list[str]:
    """
    Build TTY lines for the Coding Plan table when subscribed.

    Args:
        coding_plan: coding_plan dict from the summary payload.

    Returns:
        List of strings (empty if not subscribed).
    """
    lines = []
    if not coding_plan.get("subscribed"):
        return lines

    plan = coding_plan.get("plan", "unknown").upper()
    windows = coding_plan.get("windows", {})

    window_labels = {
        "per_5h": "Per 5 hours",
        "weekly": "This week",
        "monthly": "This month"
    }

    window_data = []
    for key, label in window_labels.items():
        window = windows.get(key, {})
        remaining = format_number(window.get("remaining", 0))
        total = format_number(window.get("total", 0))
        used_pct = window.get("used_pct", 0)
        progress = format_progress_bar(used_pct, 15)
        window_data.append({
            "label": label,
            "remaining": f"{remaining} req",
            "total": f"{total} req",
            "progress": f"[{progress}] {used_pct}% used"
        })

    col0_width = max(calc_display_width(w["label"]) for w in window_data)
    col1_width = max(calc_display_width(w["remaining"]) for w in window_data)
    col2_width = max(calc_display_width(w["total"]) for w in window_data)
    col3_width = max(calc_display_width(w["progress"]) for w in window_data)

    col0_width = max(col0_width, calc_display_width("Window"))
    col1_width = max(col1_width, calc_display_width("Remaining"))
    col2_width = max(col2_width, calc_display_width("Total"))
    col3_width = max(col3_width, calc_display_width("Progress"))

    table_width = col0_width + 1 + col1_width + 1 + col2_width + 1 + col3_width

    title_text = f"-- Coding Plan · {plan} Plan "
    title_padding = max(0, table_width - calc_display_width(title_text))
    lines.append(title_text + "-" * title_padding)

    header = f"{pad_right('Window', col0_width)} {pad_right('Remaining', col1_width)} {pad_right('Total', col2_width)} {pad_right('Progress', col3_width)}"
    lines.append(header)
    lines.append("-" * table_width)

    for w in window_data:
        row = f"{pad_right(w['label'], col0_width)} {pad_right(w['remaining'], col1_width)} {pad_right(w['total'], col2_width)} {pad_right(w['progress'], col3_width)}"
        lines.append(row)

    return lines


def _format_payg_section(payg: dict, period: dict) -> list[str]:
    """
    Build TTY lines for the Pay-as-you-go table.

    Args:
        payg: pay_as_you_go dict from the summary payload.
        period: period dict with from/to for the section title.

    Returns:
        List of strings (no leading blank line).
    """
    lines = []
    models = payg.get("models", [])
    if models:
        model_rows = []
        for model in models:
            model_id = model.get("model_id", "Unknown")
            usage = model.get("usage", {})
            units = model.get("billing_units", [])
            parts = []
            display_units = [u for u in _UNIT_DISPLAY_ORDER if u in units]
            display_units += sorted(u for u in units if u not in _UNIT_DISPLAY_ORDER)
            for u in display_units:
                usage_key, _, suffix = _get_unit_col_info(u)
                val = usage.get(usage_key, 0)
                if val:
                    parts.append(f"{format_number(val)} {suffix}")
            usage_str = ", ".join(parts) if parts else f"{format_number(usage.get('tokens_total', 0))} tok"
            cost = model.get("cost", 0)
            model_rows.append({
                "model_id": model_id,
                "usage": usage_str,
                "cost": format_cost(cost)
            })

        col0_width = max(calc_display_width(m["model_id"]) for m in model_rows)
        col1_width = max(calc_display_width(m["usage"]) for m in model_rows)
        col2_width = max(calc_display_width(m["cost"]) for m in model_rows)

        col0_width = max(col0_width, calc_display_width("Model"), calc_display_width("Total"))
        col1_width = max(col1_width, calc_display_width("Usage"))
        col2_width = max(col2_width, calc_display_width("Cost"))

        table_width = col0_width + 1 + col1_width + 1 + col2_width

        title_text = f"-- Pay-as-you-go · {period.get('from', 'N/A')} → {period.get('to', 'N/A')} "
        title_padding = max(0, table_width - calc_display_width(title_text))
        lines.append(title_text + "-" * title_padding)

        header = f"{pad_right('Model', col0_width)} {pad_right('Usage', col1_width)} {pad_right('Cost', col2_width)}"
        lines.append(header)
        lines.append("-" * table_width)

        for m in model_rows:
            row = f"{pad_right(m['model_id'], col0_width)} {pad_right(m['usage'], col1_width)} {pad_right(m['cost'], col2_width)}"
            lines.append(row)

        total = payg.get("total", {})
        total_cost = total.get("cost", 0)
        total_row = f"{pad_right('Total', col0_width)} {pad_right('—', col1_width)} {pad_right(format_cost(total_cost), col2_width)}"
        lines.append("-" * table_width)
        lines.append(total_row)
    else:
        lines.append("No pay-as-you-go usage in this period.")
    return lines


def format_table(data: dict) -> str:
    """
    Render summary data as a TTY table with dynamic column widths.

    Args:
        data: Summary payload from run_summary.

    Returns:
        Multi-line table string.
    """
    lines = []
    period = data.get("period", {})
    lines.append(f"Usage Summary  ·  {period.get('to', 'N/A')}")
    lines.append("")
    lines.extend(_format_free_tier_section(data.get("free_tier", [])))
    lines.append("")
    coding_plan = data.get("coding_plan", {})
    cp_lines = _format_coding_plan_section(coding_plan)
    lines.extend(cp_lines)
    if cp_lines:
        lines.append("")
    lines.extend(_format_payg_section(data.get("pay_as_you_go", {}), period))
    return "\n".join(lines)


def format_text(data: dict) -> str:
    """Plain-text output (no ANSI colors)."""
    return format_table(data)


def _format_usage_for_display(billing_unit: str, usage: dict) -> str:
    """
    Format a usage object as a short string for breakdown tables.

    billing_unit:
        tokens → "X tok"; images → "X img"; seconds → "X sec"; characters → "X char".
    """
    if billing_unit == "images":
        val = usage.get("images", 0)
        return f"{format_number(val)} img"
    if billing_unit == "seconds":
        val = usage.get("seconds", 0)
        return f"{format_number(val)} sec"
    if billing_unit == "characters":
        val = usage.get("characters", 0)
        return f"{format_number(val)} char"
    val = usage.get("tokens_total", 0)
    return f"{format_number(val)} tok"


def _usage_col_header(billing_unit: str) -> str:
    """Usage column header for breakdown tables."""
    return {
        "tokens": "Usage (tokens)",
        "images": "Images",
        "seconds": "Duration (sec)",
        "characters": "Characters",
    }.get(billing_unit, "Usage")


def _period_col_header(granularity: str) -> str:
    """Period column header for breakdown tables."""
    return {
        "day": "Date",
        "month": "Month",
        "quarter": "Quarter",
    }.get(granularity, "Date")


def _breakdown_title(granularity: str) -> str:
    """Title prefix for breakdown tables."""
    return {
        "day": "Daily Breakdown",
        "month": "Monthly Breakdown",
        "quarter": "Quarterly Breakdown",
    }.get(granularity, "Breakdown")


_UNIT_COL_INFO = {
    "tokens":     ("tokens_total", "Tokens",     "tok"),
    "images":     ("images",       "Images",     "img"),
    "seconds":    ("seconds",      "Duration",   "sec"),
    "characters": ("characters",   "Characters", "char"),
}

_UNIT_DISPLAY_ORDER = ["tokens", "images", "seconds", "characters"]


def _get_unit_col_info(unit: str) -> tuple:
    """
    Look up display metadata for a billing unit with graceful fallback.

    Known units return their canonical (usage_key, header, suffix) tuple.
    Unknown units return a best-effort tuple derived from the unit name itself.
    """
    if unit in _UNIT_COL_INFO:
        return _UNIT_COL_INFO[unit]
    capitalized = unit.capitalize()
    return (unit, capitalized, unit[:4])


def _group_rows_by_unit(rows: list) -> dict:
    """
    Group breakdown rows by billing unit.

    Returns dict mapping unit -> list of row dicts, each containing only the
    relevant unit's usage value.  Rows with zero usage for a given unit are
    excluded from that unit's group.
    """
    groups: dict = {}
    for row in rows:
        units = row.get("billing_units", [])
        if not units:
            units = [row.get("billing_unit", "tokens")]
        usage = row.get("usage", {})
        cost = row.get("cost", 0)

        active_units = []
        for u in units:
            usage_key = _get_unit_col_info(u)[0]
            if usage.get(usage_key, 0):
                active_units.append(u)

        if not active_units:
            active_units = units

        for u in active_units:
            if u not in groups:
                groups[u] = []
            usage_key = _get_unit_col_info(u)[0]
            groups[u].append({
                "period": row.get("period", "N/A"),
                "usage_value": usage.get(usage_key, 0),
                "cost": cost,
                "billing_unit": u,
            })
    return groups


def _format_single_unit_table(
    unit: str,
    unit_rows: list,
    granularity: str,
    period: dict,
    model_id: str,
) -> str:
    """
    Render a single-unit breakdown sub-table.

    Args:
        unit:        Billing unit key (tokens, images, seconds, characters).
        unit_rows:   List of {period, usage_value, cost, billing_unit} dicts.
        granularity: day / month / quarter.
        period:      {from, to} dict for the title line.
        model_id:    Model ID string for the title line.

    Returns:
        Multi-line table string for this unit group.
    """
    lines: list = []

    _, col_header, suffix = _get_unit_col_info(unit)
    title_prefix = _breakdown_title(granularity)
    lines.append(
        f"{title_prefix}  ·  {model_id}  ·  {col_header}"
        f"  ·  {period.get('from', 'N/A')} → {period.get('to', 'N/A')}"
    )
    lines.append("")

    if not unit_rows:
        lines.append("No pay-as-you-go usage in this period.")
        return "\n".join(lines)

    period_header = _period_col_header(granularity)

    row_data = []
    total_usage = 0.0
    total_cost = 0.0
    for r in unit_rows:
        val = r["usage_value"]
        total_usage += float(val)
        total_cost += float(r["cost"])
        row_data.append({
            "period": r["period"],
            "usage": f"{format_number(val)} {suffix}",
            "cost": format_cost(r["cost"]),
        })

    total_entry = {
        "period": "Total",
        "usage": f"{format_number(total_usage)} {suffix}" if total_usage else "—",
        "cost": format_cost(total_cost),
    }

    col_widths = {
        "period": max(
            calc_display_width(period_header),
            calc_display_width("Total"),
            max(calc_display_width(r["period"]) for r in row_data),
        ),
        "usage": max(
            calc_display_width(col_header),
            max(calc_display_width(r["usage"]) for r in row_data),
            calc_display_width(total_entry["usage"]),
        ),
        "cost": max(
            calc_display_width("Cost"),
            max(calc_display_width(r["cost"]) for r in row_data),
            calc_display_width(total_entry["cost"]),
        ),
    }

    header = (
        f"{pad_right(period_header, col_widths['period'])} "
        f"{pad_right(col_header, col_widths['usage'])} "
        f"{pad_right('Cost', col_widths['cost'])}"
    )
    lines.append(header)

    table_width = sum(col_widths.values()) + len(col_widths) - 1
    lines.append("-" * table_width)

    for r in row_data:
        lines.append(
            f"{pad_right(r['period'], col_widths['period'])} "
            f"{pad_right(r['usage'], col_widths['usage'])} "
            f"{pad_right(r['cost'], col_widths['cost'])}"
        )

    lines.append("-" * table_width)
    lines.append(
        f"{pad_right('Total', col_widths['period'])} "
        f"{pad_right(total_entry['usage'], col_widths['usage'])} "
        f"{pad_right(total_entry['cost'], col_widths['cost'])}"
    )

    return "\n".join(lines)


def format_breakdown_multi_table(data: dict) -> str:
    """
    Render breakdown data as multiple tables grouped by billing unit.

    When only one unit is present, falls back to the single-table layout
    (format_breakdown_table) for backward compatibility.
    """
    billing_units = data.get("billing_units", [])
    if not billing_units:
        billing_units = [data.get("billing_unit", "tokens")]

    if len(billing_units) <= 1:
        return format_breakdown_table(data)

    rows = data.get("rows", [])
    if not rows:
        model_id = data.get("model_id", "Unknown")
        period = data.get("period", {})
        granularity = data.get("granularity", "day")
        title_prefix = _breakdown_title(granularity)
        return (
            f"{title_prefix}  ·  {model_id}"
            f"  ·  {period.get('from', 'N/A')} → {period.get('to', 'N/A')}\n\n"
            f"No pay-as-you-go usage in this period."
        )

    groups = _group_rows_by_unit(rows)
    model_id = data.get("model_id", "Unknown")
    period = data.get("period", {})
    granularity = data.get("granularity", "day")

    sections: list = []
    known_order = [u for u in _UNIT_DISPLAY_ORDER if u in groups]
    unknown_order = sorted(u for u in groups if u not in _UNIT_DISPLAY_ORDER)
    for unit in known_order + unknown_order:
        sections.append(
            _format_single_unit_table(
                unit=unit,
                unit_rows=groups[unit],
                granularity=granularity,
                period=period,
                model_id=model_id,
            )
        )

    return "\n\n".join(sections)


def format_breakdown_table(data: dict) -> str:
    """
    Render breakdown data as a TTY table.

    Supports both single-unit (billing_unit) and multi-unit (billing_units)
    layouts. When multiple units are present, one column per unit is shown.

    Args:
        data: Breakdown payload.

    Returns:
        Multi-line table string.
    """
    lines = []

    model_id = data.get("model_id", "Unknown")
    period = data.get("period", {})
    granularity = data.get("granularity", "day")

    billing_units = data.get("billing_units", [])
    if not billing_units:
        billing_units = [data.get("billing_unit", "tokens")]

    title_prefix = _breakdown_title(granularity)
    lines.append(f"{title_prefix}  ·  {model_id}  ·  {period.get('from', 'N/A')} → {period.get('to', 'N/A')}")
    lines.append("")

    rows = data.get("rows", [])
    if not rows:
        lines.append("No pay-as-you-go usage in this period.")
        return "\n".join(lines)

    # Determine which unit columns to render (preserve canonical order,
    # then append any unknown units alphabetically)
    unit_cols = [u for u in _UNIT_DISPLAY_ORDER if u in billing_units]
    unit_cols += sorted(u for u in billing_units if u not in _UNIT_DISPLAY_ORDER)
    if not unit_cols:
        unit_cols = ["tokens"]

    period_header = _period_col_header(granularity)

    # Build per-row display strings
    row_data = []
    for row in rows:
        entry: dict = {"period": row.get("period", "N/A")}
        usage = row.get("usage", {})
        for u in unit_cols:
            usage_key, _, suffix = _get_unit_col_info(u)
            val = usage.get(usage_key, 0)
            entry[u] = f"{format_number(val)} {suffix}"
        entry["cost"] = format_cost(row.get("cost", 0))
        row_data.append(entry)

    # Build total display strings
    total_usage = data.get("total", {}).get("usage", {})
    total_entry: dict = {"period": "Total"}
    for u in unit_cols:
        usage_key, _, suffix = _get_unit_col_info(u)
        val = total_usage.get(usage_key, 0)
        total_entry[u] = f"{format_number(val)} {suffix}" if val else "—"
    total_entry["cost"] = format_cost(data.get("total", {}).get("cost", 0))

    # Calculate column widths
    col_widths: dict = {}
    col_widths["period"] = max(
        calc_display_width(period_header),
        calc_display_width("Total"),
        max(calc_display_width(r["period"]) for r in row_data),
    )
    for u in unit_cols:
        _, header_text, _ = _get_unit_col_info(u)
        col_widths[u] = max(
            calc_display_width(header_text),
            max(calc_display_width(r[u]) for r in row_data),
            calc_display_width(total_entry[u]),
        )
    col_widths["cost"] = max(
        calc_display_width("Cost"),
        max(calc_display_width(r["cost"]) for r in row_data),
        calc_display_width(total_entry["cost"]),
    )

    # Render header
    parts = [pad_right(period_header, col_widths["period"])]
    for u in unit_cols:
        _, header_text, _ = _get_unit_col_info(u)
        parts.append(pad_right(header_text, col_widths[u]))
    parts.append(pad_right("Cost", col_widths["cost"]))
    lines.append(" ".join(parts))

    table_width = sum(col_widths.values()) + len(col_widths) - 1
    lines.append("-" * table_width)

    # Render data rows
    for r in row_data:
        parts = [pad_right(r["period"], col_widths["period"])]
        for u in unit_cols:
            parts.append(pad_right(r[u], col_widths[u]))
        parts.append(pad_right(r["cost"], col_widths["cost"]))
        lines.append(" ".join(parts))

    # Render total
    lines.append("-" * table_width)
    parts = [pad_right("Total", col_widths["period"])]
    for u in unit_cols:
        parts.append(pad_right(total_entry[u], col_widths[u]))
    parts.append(pad_right(total_entry["cost"], col_widths["cost"]))
    lines.append(" ".join(parts))

    return "\n".join(lines)


def format_code_output(data: dict, group_by: str = "unit") -> str:
    """
    Wrap table output in a ```plaintext``` block for agent-friendly display.

    Args:
        data: Summary or breakdown payload.
        group_by: Grouping strategy for breakdown tables ("unit" or "none").

    Returns:
        Markdown code-fenced string.
    """
    if "model_id" in data and "rows" in data:
        table_output = _render_breakdown(data, group_by)
    else:
        table_output = format_table(data)

    return f"```plaintext\n{table_output}\n```"


def _render_breakdown(data: dict, group_by: str = "unit") -> str:
    """
    Dispatch breakdown rendering based on group_by strategy.

    Args:
        data: Breakdown payload.
        group_by: "unit" (default, multi-table by billing unit) or "none"
                  (single table with all units as columns).

    Returns:
        Rendered table string.
    """
    if group_by == "none":
        return format_breakdown_table(data)
    return format_breakdown_multi_table(data)


def format_output(data: dict, fmt: str, group_by: str = "unit") -> str:
    """
    Format structured usage data for printing.

    Args:
        data: Summary or breakdown dict.
        fmt: One of json, table, text, code, auto.

    Returns:
        Formatted string.
    """
    if fmt == "json":
        return format_json(data)
    elif fmt == "code":
        return format_code_output(data, group_by=group_by)
    elif fmt == "table" or fmt == "text":
        if "model_id" in data and "rows" in data:
            return _render_breakdown(data, group_by)
        return format_table(data)
    else:
        if "model_id" in data and "rows" in data:
            return _render_breakdown(data, group_by)
        return format_table(data)


def print_error(code: str, message: str, exit_code: int = 1):
    """
    Emit a JSON error object on stderr and exit.

    Args:
        code: Machine-readable error code.
        message: Human-readable message.
        exit_code: Process exit status.
    """
    error = {"error": {"code": code, "message": message, "exit_code": exit_code}}
    print(json.dumps(error), file=sys.stderr)
    sys.exit(exit_code)
