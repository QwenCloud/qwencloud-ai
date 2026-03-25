#!/usr/bin/env python3
"""Check for qwencloud/qwencloud-ai updates. Self-contained, stdlib only."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHECK_INTERVAL = 86400  # 24 hours

_DEFAULT_REPO = "QwenCloud/qwencloud-ai"
_REMOTE_URL_TPL = "https://raw.githubusercontent.com/{repo}/main/skills/ops/qwencloud-update-check/version.json"

# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple[int, ...]:
    """Parse '1.2.3' into (1, 2, 3) for comparison."""
    if not v or not isinstance(v, str):
        return (0, 0, 0)
    try:
        parts = v.strip().split(".")
        # Ensure we have at least 3 parts for consistent comparison
        while len(parts) < 3:
            parts.append("0")
        return tuple(int(x) for x in parts[:3])
    except (ValueError, AttributeError) as e:
        print(f"Warning: Invalid version format '{v}': {e}", file=sys.stderr)
        return (0, 0, 0)


def _is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


# ---------------------------------------------------------------------------
# Repo / path helpers
# ---------------------------------------------------------------------------

def _find_repo_root(start: Path) -> Path | None:
    for parent in [start] + list(start.parents):
        if (parent / ".agents").is_dir() and parent.name != ".agents":
            return parent
    return None


# ---------------------------------------------------------------------------
# Remote fetch
# ---------------------------------------------------------------------------

def _remote_url() -> str:
    repo = os.getenv("QWEN_SKILLS_REPO", _DEFAULT_REPO)
    return _REMOTE_URL_TPL.format(repo=repo)


def _fetch_remote_version(timeout: int = 5) -> dict | None:
    url = _remote_url()
    req = urllib.request.Request(url, headers={"User-Agent": "qwencloud/qwencloud-ai-updater"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _state_file(repo: Path) -> Path:
    return repo / ".agents" / "state.json"


def _read_repo_version() -> dict:
    vf = Path(__file__).resolve().parent.parent / "version.json"
    if vf.exists():
        try:
            return json.loads(vf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_state(repo: Path) -> dict:
    sf = _state_file(repo)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_state(state: dict, repo: Path) -> bool:
    """Write state file, return True on success, False on failure."""
    sf = _state_file(repo)
    try:
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except OSError as e:
        print(f"Warning: Failed to write state file {sf}: {e}", file=sys.stderr)
        return False


def _should_check(state: dict) -> bool:
    last = state.get("last_interaction", 0)
    return (time.time() - last) > _CHECK_INTERVAL


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def check_update(*, force: bool = False) -> dict:
    repo = _find_repo_root(Path(__file__).resolve())
    if repo is None:
        return {"has_update": False}

    state = _read_state(repo)

    if not force and not _should_check(state):
        return {"has_update": False}

    local_version = _read_repo_version().get("version", "0.1.0")
    remote_meta = _fetch_remote_version()
    if remote_meta is None:
        return {"has_update": False}

    remote_version = remote_meta.get("version", "0.1.0")
    has_update = _is_newer(remote_version, local_version)

    state["last_interaction"] = time.time()
    _write_state(state, repo)

    return {"has_update": has_update}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check for qwencloud/qwencloud-ai updates"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Bypass 24-hour rate limit and check immediately",
    )
    parser.add_argument(
        "--print-response", action="store_true",
        help="Print result as formatted JSON to stdout",
    )
    args = parser.parse_args()

    result = check_update(force=args.force)

    if args.print_response:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
