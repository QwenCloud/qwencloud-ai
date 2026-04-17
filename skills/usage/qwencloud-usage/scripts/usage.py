#!/usr/bin/env python3
"""
QwenCloud Usage skill script

Entry point: argument parsing, command dispatch, error handling.
"""

import argparse
import json
import os
import sys

from usage_lib import (
    run_summary,
    run_breakdown,
    run_logout,
    format_output,
    AuthError,
    APIError,
    print_error,
)

# ---------------------------------------------------------------------------
# Update-check signal (via symlinked shared module)
# ---------------------------------------------------------------------------

try:
    from gossamer import run as _run_update_signal_impl
except ImportError:
    _run_update_signal_impl = None  # type: ignore[assignment]

def _run_update_signal() -> None:
    if _run_update_signal_impl:
        try:
            _run_update_signal_impl(caller=__file__)
        except Exception:
            pass

def main():
    _run_update_signal()
    parser = argparse.ArgumentParser(
        description="QwenCloud Usage skill script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Login (Device Flow — opens browser for authorization)
  python usage.py login

  # View usage summary for current month
  python usage.py summary

  # View usage summary for last month
  python usage.py summary --period last-month

  # View usage summary with JSON output
  python usage.py summary --format json

  # View breakdown for specific model (last 7 days)
  python usage.py breakdown --model qwen3.6-plus --days 7

  # View breakdown for multiple models
  python usage.py breakdown --model qwen3.5-plus qwen3.6-plus --period 2026-03

  # View breakdown with custom date range
  python usage.py breakdown --model qwen-plus --from 2026-03-01 --to 2026-03-31
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # login command
    login_parser = subparsers.add_parser(
        "login", help="Authenticate via Device Flow (opens browser)"
    )
    login_parser.add_argument(
        "--force", action="store_true",
        help="Clear existing credentials and re-authenticate",
    )
    login_parser.add_argument(
        "--headless", action="store_true",
        help="Headless mode for environments without a browser (no-GUI)",
    )
    login_parser.add_argument(
        "--poll", action="store_true",
        help="Poll for authorization completion (use with --headless)",
    )

    # logout command
    logout_parser = subparsers.add_parser(
        "logout", help="Revoke session server-side and clear local credentials"
    )
    logout_parser.add_argument(
        "--token", default=None,
        help="Optional auth_token query param passed to /cli/device/logout",
    )

    # summary command
    summary_parser = subparsers.add_parser("summary", help="View usage summary")
    summary_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    summary_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    summary_parser.add_argument("--period", help="Preset period (today, yesterday, week, month, last-month, quarter, year, YYYY-MM)")
    summary_parser.add_argument("--format", choices=["table", "json", "text", "code"], default="auto", help="Output format (code: wrapped in ```plaintext)")
    summary_parser.add_argument("--poll", action="store_true",
                                help="Poll for pending headless authorization before executing")
    # breakdown command
    breakdown_parser = subparsers.add_parser("breakdown", help="View usage breakdown for a model")
    breakdown_parser.add_argument("--model", nargs="+", default=None, metavar="MODEL_ID", help="Model ID(s) to filter (space-separated); omit to query all models")
    breakdown_parser.add_argument("--granularity", choices=["day", "month", "quarter"], default="day", help="Time granularity")
    breakdown_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    breakdown_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    breakdown_parser.add_argument("--period", help="Preset period")
    breakdown_parser.add_argument("--days", type=int, help="Last N days")
    breakdown_parser.add_argument("--format", choices=["table", "json", "text", "code"], default="auto", help="Output format (code: wrapped in ```plaintext)")
    breakdown_parser.add_argument("--poll", action="store_true", help="Poll for pending headless authorization before executing")
    breakdown_parser.add_argument("--group-by", dest="group_by", choices=["unit", "none"], default="unit", help="Group breakdown tables: 'unit' splits by billing unit (default), 'none' uses single table")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # ── login command ──────────────────────────────────────────────────
    if args.command == "login":
        from device_flow import is_headless_mode
        if getattr(args, "headless", False) or is_headless_mode():
            if getattr(args, "poll", False):
                _handle_headless_poll(args)
            else:
                _handle_headless_start(args)
        else:
            _handle_login(args)
        return

    # ── logout command ─────────────────────────────────────────────────
    if args.command == "logout":
        run_logout(args)
        return

    # ── summary / breakdown ────────────────────────────────────────────
    try:
        result = _execute_with_retry(args)
        group_by = getattr(args, "group_by", "unit")
        output = format_output(result, args.format, group_by=group_by)
        print(output)

    except AuthError as e:
        print_error("AUTH_REQUIRED", str(e), exit_code=2)
    except APIError as e:
        print_error("API_ERROR", str(e), exit_code=3)
    except ValueError as e:
        print_error("INVALID_INPUT", str(e), exit_code=1)
    except Exception as e:
        print_error("UNKNOWN", str(e), exit_code=1)


# ═══════════════════════════════════════════════════════════════════════════════
# login handler
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_login(args):
    """Explicitly trigger Device Flow login and persist credentials."""
    from credential_store import get_cli_store
    from device_flow import device_flow_login, is_token_expired, DeviceFlowError

    cli_store = get_cli_store()

    if getattr(args, "force", False):
        cli_store.clear()
    else:
        creds = cli_store.load()
        if creds and not is_token_expired(creds):
            user = creds.get("user") or {}
            email = user.get("Email", user.get("email", ""))
            expires = creds.get("expires_at", "unknown")
            print("Already logged in.", file=sys.stderr)
            if email:
                print(f"  User: {email}", file=sys.stderr)
            print(f"  Expires: {expires}", file=sys.stderr)
            print(
                "Run with --force to clear credentials and re-authenticate.",
                file=sys.stderr,
            )
            return

    try:
        creds = device_flow_login()
    except DeviceFlowError as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(2)

    cli_store.save(creds)
    print("Credentials saved.", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════════════════
# headless login handlers
# ═══════════════════════════════════════════════════════════════════════════════

def _handle_headless_start(args):
    """Phase 1: request device code, save pending session, print URL."""
    from credential_store import get_cli_store
    from device_flow import (
        device_flow_start, is_token_expired, DeviceFlowError,
    )

    cli_store = get_cli_store()

    if getattr(args, "force", False):
        cli_store.clear()
    else:
        creds = cli_store.load()
        if creds and not is_token_expired(creds):
            user = creds.get("user") or {}
            email = user.get("Email", user.get("email", ""))
            expires = creds.get("expires_at", "unknown")
            result = {"status": "already_logged_in", "expires_at": expires}
            if email:
                result["user"] = email
            print(json.dumps(result))
            print("Already logged in.", file=sys.stderr)
            return

    try:
        session = device_flow_start()
    except DeviceFlowError as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        print(f"Login start failed: {e}", file=sys.stderr)
        sys.exit(2)

    print(
        f"\n[device-flow] To sign in, open this URL in your browser:\n"
        f"\n  {session['verification_url']}\n",
        file=sys.stderr,
    )
    print(
        "[device-flow] Then run with --poll to complete login.\n",
        file=sys.stderr,
    )

    print(json.dumps({
        "status": "pending",
        "verification_url": session["verification_url"],
        "expires_in": session["expires_in"],
    }))


def _handle_headless_poll(args):
    """Phase 2: poll for authorization using a saved pending session."""
    from credential_store import get_cli_store
    from device_flow import (
        device_flow_poll, is_token_expired, DeviceFlowError,
    )

    cli_store = get_cli_store()

    # Fast path: credentials may already exist (another process completed login)
    creds = cli_store.load()
    if creds and not is_token_expired(creds):
        user = creds.get("user") or {}
        email = user.get("Email", user.get("email", ""))
        result = {"status": "complete"}
        if email:
            result["user"] = email
        print(json.dumps(result))
        print("Already logged in.", file=sys.stderr)
        return

    try:
        creds = device_flow_poll()
    except DeviceFlowError as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        print(f"Login poll failed: {e}", file=sys.stderr)
        sys.exit(2)

    cli_store.save(creds)
    print("Credentials saved.", file=sys.stderr)

    user = creds.get("user") or {}
    email = user.get("Email", user.get("email", ""))
    result = {"status": "complete"}
    if email:
        result["user"] = email
    print(json.dumps(result))


# ═══════════════════════════════════════════════════════════════════════════════
# retry logic
# ═══════════════════════════════════════════════════════════════════════════════

def _execute_with_retry(args) -> dict:
    """
    Execute the command with one-shot token refresh on expiry.

    CLI mode: retry with force_refresh=True (triggers Device Flow re-login).
    """
    runner = run_summary if args.command == "summary" else run_breakdown

    try:
        return runner(args)
    except AuthError as e:
        if "expired" not in str(e).lower():
            raise

    return runner(args, force_refresh=True)


if __name__ == "__main__":
    main()