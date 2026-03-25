#!/usr/bin/env python3
"""Shared update-check signal emitter for qwencloud/qwencloud-ai.

Detects whether qwencloud-update-check is installed and emits structured
signals to stderr that agents can parse and act on:

  [ACTION_REQUIRED]  — qwencloud-update-check is not installed
  [UPDATE_AVAILABLE]  — a newer version is available

Self-contained, stdlib only.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SKILLS_REPO = "QwenCloud/qwencloud-ai"

INSTALL_CMD = f"npx skills add {_SKILLS_REPO} --skill qwencloud-update-check -y"


_FATIGUE_INTERVAL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_repo_root(start: Path) -> Path | None:
    for parent in [start] + list(start.parents):
        if (parent / ".agents").is_dir() and parent.name != ".agents":
            return parent
    return None


def _state_file(repo: Path) -> Path:
    return repo / ".agents" / "state.json"


def _read_state(repo: Path) -> dict:
    sf = _state_file(repo)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _write_state(state: dict, repo: Path) -> None:
    sf = _state_file(repo)
    try:
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass

def _read_installed_skills(repo: Path) -> list[str]:
    lf = repo / "skills-lock.json"
    if lf.exists():
        try:
            data = json.loads(lf.read_text(encoding="utf-8"))
            skills = data.get("skills", {})
            if isinstance(skills, dict):
                return sorted(k for k in skills if k.startswith("qwencloud-"))
        except (json.JSONDecodeError, OSError):
            pass
    return []

def _build_update_cmd(repo: Path) -> str:
    skills = _read_installed_skills(repo)
    skill_args = " ".join(skills) if skills else ""
    return f"npx skills add {_SKILLS_REPO} --skill {skill_args} -y"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(caller: str | Path | None = None) -> None:
    """Check update status and emit structured signals to stderr.

    Parameters
    ----------
    caller : str or Path, optional
        ``__file__`` of the calling script — used to locate the repo root.
        Falls back to this module's own ``__file__`` if omitted.
    """
    origin = Path(caller).resolve() if caller else Path(__file__).resolve()
    repo = _find_repo_root(origin)
    if repo is None:
        return

    state = _read_state(repo)
    if state.get("never_install"):
        return
    ts = state.get("last_interaction", 0)
    if (time.time() - ts) < _FATIGUE_INTERVAL:
        return

    # Look for qwencloud-update-check in known locations
    for subdir in ("ops/qwencloud-update-check", "qwencloud-update-check"):
        skill_dir = repo / "skills" / subdir

        if not skill_dir.is_dir():
            skill_dir = repo / ".agents" / "skills" / subdir

        if skill_dir.is_dir():
            script = skill_dir / "scripts" / "check_update.py"
            if not script.is_file():
                return
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "--print-response"],
                    capture_output=True, text=True, timeout=15,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    result = json.loads(proc.stdout)
                    if result.get("has_update"):
                        cmd = _build_update_cmd(repo)
                        print(
                            f"\n[UPDATE_AVAILABLE] qwencloud/qwencloud-ai has a newer version available.",
                            file=sys.stderr,
                        )
                        print(f"  Run: {cmd}\n", file=sys.stderr)

            except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
                pass
            return
    dismiss_install_prompt()
    print(
        f"[ACTION_REQUIRED] qwencloud-update-check skill is not installed. "
        f"Install: {INSTALL_CMD}",
        file=sys.stderr,
    )


def dismiss_install_prompt() -> None:
    """Record a user interaction timestamp.

    Suppresses all update-check signals for 24 hours.
    Called after both "Install now" and "Skip for now".
    """
    repo = _find_repo_root(Path(__file__).resolve())
    if repo is None:
        return
    state = _read_state(repo)
    state["last_interaction"] = time.time()
    _write_state(state, repo)


def never_install_prompt() -> None:
    """Record that the user chose to never install qwencloud-update-check.

    Permanently suppresses all update-check signals.
    """
    repo = _find_repo_root(Path(__file__).resolve())
    if repo is None:
        return
    state = _read_state(repo)
    state["never_install"] = True
    _write_state(state, repo)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage update-check preferences")
    parser.add_argument("--never-install", action="store_true",
                        help="Permanently suppress update-check prompts")
    parser.add_argument("--dismiss", action="store_true",
                        help="Suppress update-check prompts for 24 hours")
    args = parser.parse_args()
    if args.never_install:
        never_install_prompt()
        print("Update-check prompts permanently suppressed.", file=sys.stderr)
    elif args.dismiss:
        dismiss_install_prompt()
        print("Update-check prompts suppressed for 24 hours.", file=sys.stderr)
