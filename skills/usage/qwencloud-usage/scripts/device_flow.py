#!/usr/bin/env python3
"""
QwenCloud Device Flow Login

OAuth 2.0 Device Authorization Flow for CLI-based authentication.
Designed for environments where a browser is available on the same machine
but the CLI itself cannot host a redirect URI.

Protocol reference: ref/usage-api/default-login-and-req-api-flow.md

Flow:
  1. Generate / load a persistent client_id (UUID v4 stored in ~/.qwencloud/device)
  2. POST /cli/device/code → obtain device_token + verification_url
  3. Open verification_url in the system browser
  4. Poll /cli/device/token until the user completes authorization
  5. Return credentials {access_token, refresh_token, expires_at, user}
"""

import base64
import hashlib
import json
import os
import random
import secrets
import stat
import sys
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_AUTH_ENDPOINT = "https://t.qwencloud.com"
DEFAULT_API_ENDPOINT = "https://cli.qwencloud.com"

_QWENCLOUD_DIR = Path.home() / ".qwencloud"
_DEVICE_ID_FILE = _QWENCLOUD_DIR / "device"
_PENDING_SESSION_FILE = _QWENCLOUD_DIR / "pending_device_flow.json"

def _poll_backoff_enabled() -> bool:
    """Backoff with jitter is always enabled."""
    return True


def is_headless_mode() -> bool:
    """Detect whether the current environment lacks a usable browser.

    Auto-detection checks: SSH session, container, no DISPLAY, no browser.
    """
    # ── Auto-detect: SSH session ───────────────────────────────────────
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True

    # ── Auto-detect: Linux without display server ──────────────────────
    if sys.platform.startswith("linux"):
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return True

    # ── Auto-detect: container environment ─────────────────────────────
    if Path("/.dockerenv").exists():
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            cgroup = f.read()
        if "docker" in cgroup or "kubepods" in cgroup:
            return True
    except (FileNotFoundError, PermissionError):
        pass

    # ── Auto-detect: no usable browser ─────────────────────────────────
    try:
        webbrowser.get()
    except webbrowser.Error:
        return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# PKCE (Proof Key for Code Exchange) — RFC 7636
# ═══════════════════════════════════════════════════════════════════════════════

def _pkce_enabled() -> bool:
    """PKCE is always enabled (mandatory for all clients)."""
    return True


def _generate_code_verifier(length: int = 64) -> str:
    """RFC 7636 Section 4.1: 43-128 char URL-safe random string."""
    return secrets.token_urlsafe(length)[:128]


def _compute_code_challenge(verifier: str) -> str:
    """RFC 7636 Section 4.2: BASE64URL(SHA256(code_verifier)), no padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ═══════════════════════════════════════════════════════════════════════════════
# Client ID Management
# ═══════════════════════════════════════════════════════════════════════════════

def get_or_create_client_id() -> str:
    """
    Return a persistent device UUID.  Creates ~/.qwencloud/device on first use.
    """
    if _DEVICE_ID_FILE.exists():
        try:
            content = _DEVICE_ID_FILE.read_text("utf-8").strip()
            if content:
                return content
        except OSError:
            pass

    client_id = str(uuid.uuid4())
    try:
        _QWENCLOUD_DIR.mkdir(parents=True, exist_ok=True)
        _DEVICE_ID_FILE.write_text(client_id, encoding="utf-8")
        if os.name != "nt":
            os.chmod(_DEVICE_ID_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        print(
            f"[device-flow] Warning: could not persist device id: {e}",
            file=sys.stderr,
        )
    return client_id


# ═══════════════════════════════════════════════════════════════════════════════
# Token Expiry Check
# ═══════════════════════════════════════════════════════════════════════════════

def is_token_expired(creds: dict) -> bool:
    """
    Return True if the credential's expires_at is in the past (or missing).
    Accepts ISO 8601 strings with or without timezone.
    """
    expires_at = creds.get("expires_at")
    if not expires_at:
        return True
    try:
        if isinstance(expires_at, str):
            ts = expires_at.replace("Z", "+00:00")
            exp = datetime.fromisoformat(ts)
        else:
            return True
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= exp
    except (ValueError, TypeError):
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Helpers
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceFlowError(Exception):
    """Raised when the Device Flow fails irrecoverably."""


def _post(url: str, timeout: int = 15) -> dict:
    """POST with empty body, return parsed JSON response."""
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        raise DeviceFlowError(
            f"HTTP {e.code} from {url}: {body}"
        ) from e
    except urllib.error.URLError as e:
        raise DeviceFlowError(f"Network error: {e.reason}") from e


# ═══════════════════════════════════════════════════════════════════════════════
# Browser Open (standard https:// URLs — webbrowser module is fine)
# ═══════════════════════════════════════════════════════════════════════════════

def _open_browser(url: str) -> None:
    """Best-effort open a standard URL in the system browser."""
    try:
        webbrowser.open(url)
    except Exception:
        print(
            f"[device-flow] Could not open browser automatically.\n"
            f"  Please open this URL manually: {url}",
            file=sys.stderr,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Device Flow Core
# ═══════════════════════════════════════════════════════════════════════════════

def device_flow_login(
    auth_endpoint: str = DEFAULT_AUTH_ENDPOINT,
) -> dict:
    """
    Execute the full OAuth 2.0 Device Flow and return credentials.

    Returns:
        {
            "access_token": str,
            "refresh_token": str | None,
            "expires_at": str (ISO 8601),
            "user": {"id": ..., "email": ..., "organization": ...} | None,
            "auth_mode": "device_flow",
        }

    Raises:
        DeviceFlowError on failure (network, denied, timeout, bad response).
    """
    client_id = get_or_create_client_id()

    use_pkce = _pkce_enabled()
    code_verifier = _generate_code_verifier() if use_pkce else None
    code_challenge = _compute_code_challenge(code_verifier) if use_pkce else None

    # Phase 1: Request device code
    init_url = (
        f"{auth_endpoint}/cli/device/code?"
        f"client_id={urllib.parse.quote(client_id, safe='')}"
    )
    if use_pkce:
        init_url += (
            f"&code_challenge={urllib.parse.quote(code_challenge, safe='')}"
            f"&code_challenge_method=S256"
        )
    resp = _post(init_url)
    if not resp.get("Success"):
        raise DeviceFlowError(f"Device code request failed: {resp}")

    data = resp.get("Data", {})
    device_token = data.get("Token")
    verification_url = data.get("VerificationUrl")
    expires_in = int(data.get("ExpiresIn", 900))
    interval = int(data.get("Interval", 5))

    if not device_token or not verification_url:
        raise DeviceFlowError(f"Missing Token or VerificationUrl in response: {data}")

    # Phase 2: Show URL and open browser
    print(
        f"\n[device-flow] To sign in, open this URL in your browser:\n"
        f"\n  {verification_url}\n",
        file=sys.stderr,
    )
    _open_browser(verification_url)
    print("[device-flow] Waiting for authorization ...\n", file=sys.stderr)

    # Phase 3: Poll for authorization
    poll_url_base = (
        f"{auth_endpoint}/cli/device/token?"
        f"client_id={urllib.parse.quote(client_id, safe='')}"
        f"&token={urllib.parse.quote(device_token, safe='')}"
    )
    if use_pkce:
        poll_url_base += (
            f"&code_verifier={urllib.parse.quote(code_verifier, safe='')}"
        )

    max_attempts = expires_in // interval
    current_interval = interval
    deadline = time.monotonic() + expires_in

    for attempt in range(1, max_attempts + 1):
        # Check deadline before sleeping — if slow_down increased the
        # interval, the original max_attempts may overshoot expires_in.
        time_left = deadline - time.monotonic()
        if time_left <= 0:
            break
        actual_sleep = min(current_interval, time_left)
        time.sleep(actual_sleep)

        try:
            poll_resp = _post(poll_url_base)
        except DeviceFlowError:
            continue

        if not poll_resp.get("Success"):
            continue

        poll_data = poll_resp.get("Data", {})
        status = poll_data.get("Status", "").lower()

        if status == "authorization_pending":
            continue

        if status == "slow_down":
            current_interval += 2
            # Recalculate max_attempts based on remaining time
            remaining = deadline - time.monotonic()
            max_attempts = attempt + max(1, int(remaining // current_interval))
            continue

        if status == "access_denied":
            raise DeviceFlowError("Authorization was denied by the user.")

        if status == "expired_token":
            raise DeviceFlowError(
                "Device code expired. Please run the login command again."
            )

        if status == "complete":
            creds_raw = poll_data.get("Credentials", {})
            access_token = creds_raw.get("AccessToken")
            if not access_token:
                raise DeviceFlowError(
                    f"No AccessToken in complete response: {creds_raw}"
                )

            result = {
                "access_token": access_token,
                "refresh_token": creds_raw.get("RefreshToken"),
                "expires_at": creds_raw.get("ExpireTime", ""),
                "user": creds_raw.get("User"),
                "auth_mode": "device_flow",
            }
            print("[device-flow] Login successful!", file=sys.stderr)
            if result.get("user"):
                user = result["user"]
                email = user.get("Email", user.get("email", ""))
                if email:
                    print(f"[device-flow] Logged in as: {email}", file=sys.stderr)
            return result

    raise DeviceFlowError(
        f"Authorization timed out after {expires_in}s. "
        "Please run the login command again."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Pending Session File Management (headless two-phase login)
# ═══════════════════════════════════════════════════════════════════════════════

def _save_pending_session(data: dict) -> None:
    """Atomically write pending device flow session to disk (mode 0o600)."""
    _QWENCLOUD_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = str(_PENDING_SESSION_FILE) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp_path, str(_PENDING_SESSION_FILE))
    if os.name != "nt":
        os.chmod(_PENDING_SESSION_FILE, stat.S_IRUSR | stat.S_IWUSR)


def _load_pending_session() -> Optional[dict]:
    """Load and validate the pending session file.

    Returns the session dict if the file exists and has not expired,
    otherwise returns None (and removes a stale file).
    """
    if not _PENDING_SESSION_FILE.exists():
        return None
    try:
        with open(_PENDING_SESSION_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        _clear_pending_session()
        return None

    expires_at = data.get("expires_at", "")
    if not expires_at:
        _clear_pending_session()
        return None

    try:
        ts = expires_at.replace("Z", "+00:00")
        exp = datetime.fromisoformat(ts)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= exp:
            _clear_pending_session()
            return None
    except (ValueError, TypeError):
        _clear_pending_session()
        return None

    return data


def _clear_pending_session() -> None:
    """Remove the pending session file if it exists."""
    try:
        _PENDING_SESSION_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def load_pending_session() -> Optional[dict]:
    """Public accessor for pending session data (used by usage_lib)."""
    return _load_pending_session()


# ═══════════════════════════════════════════════════════════════════════════════
# Headless Device Flow — Two-Phase API
# ═══════════════════════════════════════════════════════════════════════════════

def device_flow_start(
    auth_endpoint: str = DEFAULT_AUTH_ENDPOINT,
) -> dict:
    """Phase 1: request a device code and persist the pending session.

    This function does **not** open a browser or enter a polling loop.
    It is designed for headless / no-GUI environments where the user will
    open the verification URL on a separate device.

    Returns:
        {
            "verification_url": str,
            "device_token": str,
            "client_id": str,
            "code_verifier": str | None,
            "auth_endpoint": str,
            "expires_at": str (ISO 8601),
            "expires_in": int,
            "interval": int,
        }

    Raises:
        DeviceFlowError on network or protocol failure.
    """
    client_id = get_or_create_client_id()

    use_pkce = _pkce_enabled()
    code_verifier = _generate_code_verifier() if use_pkce else None
    code_challenge = _compute_code_challenge(code_verifier) if use_pkce else None

    init_url = (
        f"{auth_endpoint}/cli/device/code?"
        f"client_id={urllib.parse.quote(client_id, safe='')}"
    )
    if use_pkce:
        init_url += (
            f"&code_challenge={urllib.parse.quote(code_challenge, safe='')}"
            f"&code_challenge_method=S256"
        )

    resp = _post(init_url)
    if not resp.get("Success"):
        raise DeviceFlowError(f"Device code request failed: {resp}")

    data = resp.get("Data", {})
    device_token = data.get("Token")
    verification_url = data.get("VerificationUrl")
    expires_in = int(data.get("ExpiresIn", 900))
    interval = int(data.get("Interval", 5))

    if not device_token or not verification_url:
        raise DeviceFlowError(
            f"Missing Token or VerificationUrl in response: {data}"
        )

    from datetime import timedelta as _td
    expires_at_dt = datetime.now(timezone.utc) + _td(seconds=expires_in)
    expires_at_str = expires_at_dt.isoformat()

    session = {
        "verification_url": verification_url,
        "device_token": device_token,
        "client_id": client_id,
        "code_verifier": code_verifier,
        "auth_endpoint": auth_endpoint,
        "expires_at": expires_at_str,
        "expires_in": expires_in,
        "interval": interval,
    }
    _save_pending_session(session)

    return session


def device_flow_poll() -> dict:
    """Phase 2: poll for authorization using a previously saved pending session.

    Reads the pending session file written by ``device_flow_start()``,
    polls the token endpoint until the user completes authorization,
    then clears the pending file and returns credentials.

    Returns:
        {
            "access_token": str,
            "refresh_token": str | None,
            "expires_at": str (ISO 8601),
            "user": dict | None,
            "auth_mode": "device_flow",
        }

    Raises:
        DeviceFlowError when no pending session exists, session expired,
        or authorization fails.
    """
    session = _load_pending_session()
    if not session:
        raise DeviceFlowError(
            "No pending login session found. "
            "Run 'login --headless' first to start the Device Flow."
        )

    client_id = session["client_id"]
    device_token = session["device_token"]
    code_verifier = session.get("code_verifier")
    auth_endpoint = session.get("auth_endpoint", DEFAULT_AUTH_ENDPOINT)
    interval = session.get("interval", 5)

    expires_at_str = session["expires_at"]
    try:
        ts = expires_at_str.replace("Z", "+00:00")
        exp = datetime.fromisoformat(ts)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        remaining_seconds = max(
            0, int((exp - datetime.now(timezone.utc)).total_seconds())
        )
    except (ValueError, TypeError):
        remaining_seconds = 0

    if remaining_seconds <= 0:
        _clear_pending_session()
        raise DeviceFlowError(
            "Pending device code has expired. "
            "Run 'login --headless' again to start a new session."
        )

    poll_url_base = (
        f"{auth_endpoint}/cli/device/token?"
        f"client_id={urllib.parse.quote(client_id, safe='')}"
        f"&token={urllib.parse.quote(device_token, safe='')}"
    )
    if code_verifier:
        poll_url_base += (
            f"&code_verifier={urllib.parse.quote(code_verifier, safe='')}"
        )

    current_interval = interval

    # Pre-generate the full sleep schedule so total time never exceeds the
    # remaining window.  Each entry is popped in order; when the list is
    # exhausted the loop ends — this provides a natural attempt-count cap.
    #
    # Jitter strategy: "Clamped Full Jitter" — each sleep is
    # uniform(interval, base * 1.5) where base = interval * backoff_factor.
    # The lower bound equals the server-mandated minimum interval, so we
    # never trigger slow_down.  The upper bound grows with backoff, giving
    # progressively wider scatter for concurrent clients.
    sleep_queue: list[float] = []
    cumulative = 0.0
    seq = 0
    while True:
        seq += 1
        if _poll_backoff_enabled():
            backoff_factor = min(1.0 + seq * 0.05, 2.0)
            upper = current_interval * backoff_factor * 1.5
            sleep_val = random.uniform(current_interval, upper)
        else:
            sleep_val = float(current_interval)
        if cumulative + sleep_val > remaining_seconds:
            # Squeeze in one last shorter sleep if there is room
            leftover = remaining_seconds - cumulative
            if leftover >= 1.0:
                sleep_queue.append(leftover)
            break
        sleep_queue.append(sleep_val)
        cumulative += sleep_val

    total_polls = len(sleep_queue)

    print("[device-flow] Waiting for authorization ...\n", file=sys.stderr)

    for attempt, sleep_time in enumerate(sleep_queue, 1):
        time.sleep(sleep_time)

        try:
            poll_resp = _post(poll_url_base)
        except DeviceFlowError:
            continue

        if not poll_resp.get("Success"):
            continue

        poll_data = poll_resp.get("Data", {})
        status = poll_data.get("Status", "").lower()

        if status == "authorization_pending":
            continue

        if status == "slow_down":
            current_interval += 2
            # Append extra polls with the new interval + clamped jitter
            elapsed = sum(sleep_queue[:attempt])
            budget_left = remaining_seconds - elapsed
            while budget_left >= current_interval:
                jittered = random.uniform(
                    current_interval, current_interval * 1.5,
                )
                if jittered > budget_left:
                    if budget_left >= current_interval:
                        sleep_queue.append(budget_left)
                    break
                sleep_queue.append(jittered)
                budget_left -= jittered
            total_polls = len(sleep_queue)
            continue

        if status == "access_denied":
            _clear_pending_session()
            raise DeviceFlowError("Authorization was denied by the user.")

        if status == "expired_token":
            _clear_pending_session()
            raise DeviceFlowError(
                "Device code expired. Run 'login --headless' again."
            )

        if status == "complete":
            creds_raw = poll_data.get("Credentials", {})
            access_token = creds_raw.get("AccessToken")
            if not access_token:
                raise DeviceFlowError(
                    f"No AccessToken in complete response: {creds_raw}"
                )

            result = {
                "access_token": access_token,
                "refresh_token": creds_raw.get("RefreshToken"),
                "expires_at": creds_raw.get("ExpireTime", ""),
                "user": creds_raw.get("User"),
                "auth_mode": "device_flow",
            }
            _clear_pending_session()
            print("[device-flow] Login successful!", file=sys.stderr)
            if result.get("user"):
                user = result["user"]
                email = user.get("Email", user.get("email", ""))
                if email:
                    print(
                        f"[device-flow] Logged in as: {email}",
                        file=sys.stderr,
                    )
            return result

    _clear_pending_session()
    raise DeviceFlowError(
        f"Authorization timed out ({remaining_seconds}s, "
        f"{total_polls} polls exhausted). "
        "Run 'login --headless' again to start a new session."
    )
