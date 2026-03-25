---
name: qwencloud-update-check
description: "[QwenCloud] Check for qwencloud-ai updates and notify the user when a new version is available. TRIGGER when: user asks to check for updates, check version, asks 'is there a new version', 'latest version', 'update skills', 'check update', or any other qwen skill delegates to this skill, or user explicitly invokes this skill by name (e.g. use qwencloud-update-check). DO NOT TRIGGER when: non-update-related tasks, general version questions about other software."
compatibility: "Requires Python 3.9+ and curl. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

# Qwen Update Checker

Automatic version checker for the **qwencloud/qwencloud-ai** skill pack. Compares the locally installed version against the latest release on GitHub and notifies the user when an update is available.

This skill is referenced by all other qwencloud/qwencloud-ai. When any skill runs, it checks if this skill is installed and delegates version checking here.

## How It Works

1. Reads the installed version from `version.json` (the `version` field bundled with this skill).
2. Fetches the latest version from the remote repository (GitHub raw content).
3. Compares versions using semver. Returns `{"has_update": true}` if a newer version exists.
4. Records the check timestamp (`last_interaction`) in `<repo_root>/.agents/state.json` to rate-limit network requests to once every 24 hours.

## Usage

Other skills invoke this script automatically. You can also run it manually:

```bash
python3 <path-to-this-skill>/scripts/check_update.py --print-response
```

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `--print-response` | Print result as formatted JSON to stdout |
| `--force` | Bypass 24-hour rate limit and check immediately |

### Output Format

```json
{
  "has_update": true
}
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `QWEN_SKILLS_REPO` | `qwencloud/qwencloud-ai` | GitHub repo for remote version check |

## State File

The `last_interaction` timestamp is stored at `<repo_root>/.agents/state.json` for rate-limiting. Check results are **not** cached in the state file. This file persists across sessions and is shared with `gossamer.py` for fatigue control.
