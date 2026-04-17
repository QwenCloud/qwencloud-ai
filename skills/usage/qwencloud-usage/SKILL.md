---
name: qwencloud-usage
description: "[QwenCloud] Manage account auth and query usage/billing. Use for: login, logout, check usage, view billing, free tier quota, coding plan status, pay-as-you-go costs. Skip for: model browsing, non-account tasks."
---

# QwenCloud Usage

Query QwenCloud usage, free tier quota, coding plan status, and pay-as-you-go billing.

## Prerequisites

- Install dependencies before first use:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r <path-to-skill>/scripts/requirements.txt
```

- Authentication: No configuration needed on first use (Device Flow auto-login).

### Environment Variables

| Variable                    | Description                                                                                  |
|-----------------------------|----------------------------------------------------------------------------------------------|
| `QWENCLOUD_CREDENTIALS_DIR` | Override encrypted file backend directory (default: `~/.qwencloud/secure-store`).            |

## Usage

```bash
python3 <path-to-skill>/scripts/usage.py <command> [options]
```

### Commands

**`login`** — Authenticate via Device Flow (opens browser)

```bash
python3 scripts/usage.py login
```

**`login --headless`** — Headless login for environments without a browser (e.g. remote servers, containers, agent runtimes)

```bash
# Step 1: Start login and get the verification URL
python3 scripts/usage.py login --headless
# Output (stdout): {"status": "pending", "verification_url": "https://...", "expires_in": 900}

# Step 2: User opens the URL in a browser on another device and completes authorization

# Step 3: Poll for authorization completion
python3 scripts/usage.py login --headless --poll
# Output (stdout): {"status": "complete", "user": "user@example.com"}
```

Note: If you skip the explicit `--poll` step and directly run `summary` or `breakdown`, the script will automatically detect the pending session and poll for authorization.

**`logout`** — Revoke session server-side and clear local credentials

```bash
python3 scripts/usage.py logout
python3 scripts/usage.py logout --token <auth_token>   # pass explicit auth_token query param
```

**`summary`** — View usage summary (free tier, coding plan, pay-as-you-go)

```bash
python3 scripts/usage.py summary                      # Current month
python3 scripts/usage.py summary --period last-month  # Last month
python3 scripts/usage.py summary --from 2026-03-01 --to 2026-03-31
python3 scripts/usage.py summary --format json        # JSON output
```

**Period presets**: `today`, `yesterday`, `week`, `month` (default), `last-month`, `quarter`, `year`, `YYYY-MM`

**`breakdown`** — View model usage breakdown

```bash
python3 scripts/usage.py breakdown --model qwen3.6-plus --days 7
python3 scripts/usage.py breakdown --model qwen3.5-plus qwen3.6-plus --period 2026-03
python3 scripts/usage.py breakdown --model qwen-plus --period 2026-03 --granularity month
python3 scripts/usage.py breakdown --period 2026-03   # all models
```

### Breakdown Parameters: How to Think About Them

**Three independent dimensions — combine them freely:**

`--model` (optional) + **date range** + **granularity**

**Model scope:**
- `--model <id>` — single model (e.g. `qwen3.5-plus`)
- `--model <id1> <id2> ...` — multiple models space-separated (e.g. `--model qwen3.5-plus qwen3.6-plus`)
- omit `--model` — queries all models; useful for "how much did I spend in total" questions

**Date range** — three patterns, pick by how the user described the period:

| Pattern | When to use | How it works |
|---|---|---|
| `--period YYYY-MM` | User names a specific month ("March", "last April") | Exact calendar month, start to end |
| `--period <preset>` | User describes a relative period | `last-month` = previous full month; `month` = this month so far; `quarter` = this calendar quarter so far |
| `--days N` | User says "last N days" | Rolling window backwards from today, crosses month boundaries naturally |
| `--from YYYY-MM-DD --to YYYY-MM-DD` | User gives explicit dates or a named quarter/range | Full control, use when other patterns don't fit |

**Granularity** — determines the grouping of results, not the range:

- `day` (default) — one row per day; good for spotting usage spikes
- `month` — one row per calendar month; good for multi-month trends
- `quarter` — one row per quarter; good for Q-over-Q comparison

The script automatically splits any range into per-month API calls — the granularity only affects how rows are grouped in the output, not what the API receives.

**Classic examples:**
```bash
# Single model, single month, daily detail
breakdown --model qwen3.5-plus --period 2026-03

# Multiple models, single month, daily detail
breakdown --model qwen3.5-plus qwen3.6-plus --period 2026-03

# Single model, last 3 months, monthly summary
breakdown --model qwen3.5-plus --days 90 --granularity month

# Single model, specific quarter, quarterly rollup
breakdown --model qwen3.5-plus --from 2026-01-01 --to 2026-03-31 --granularity quarter

# All models, this month, daily breakdown
breakdown --period month
```

## Output Example

```plaintext
Usage Summary  ·  2026-04-10

-- Free Tier Quota -------------------------------------------------------
Model                Remaining      Total          Progress
qwen3.6-plus         850K tokens    1M tokens      [████████████░░░] 85% left
wan2.6-t2i           38 images      50 images      [█████████░░░░░░] 76% left
--------------------------------------------------------------------------

-- Coding Plan · PRO Plan ------------------------------------------------
Window           Remaining      Total          Progress
Per 5 hours      4.8K req       6K req         [████░░░░░░░░░] 20% used
This week        38.2K req      45K req        [███░░░░░░░░░░] 15% used
This month       82.5K req      90K req        [██░░░░░░░░░░░]  8% used
--------------------------------------------------------------------------

-- Pay-as-you-go · 2026-04-01 → 2026-04-10 -------------------------------
Model                Requests     Usage              Cost
qwen3.6-plus         240          480K tok           $0.38
qwen-plus            920          460K tok           $0.13
--------------------------------------------------------------------------
Total                1.2K         —                  $0.51
```

## ⚠️ CRITICAL: Agent Output Rules

**When executing this skill, you MUST:**

1. **Display script output EXACTLY AS-IS** — no modification, no reformatting
2. **Preserve all formatting** — alignment, spacing, progress bars, separators
3. **Add analysis AFTER output only** — clearly separated with `---`

**NEVER:**
- ❌ Reformat or summarize the table
- ❌ Add prefixes like "Here's your usage:"
- ❌ Convert to bullet points or different format

**✅ CORRECT:**
```
[Script output - exactly as-is]

---

**💡 Analysis**: Your qwen3.6-plus free tier is 85% remaining...
```

**❌ WRONG:**
```
Here's your usage:
- qwen3.6-plus: 850K tokens remaining (85% left)
```

## ⚠️ Headless Login: Agent Behavior

When the script exits with code 2 and stderr contains `[device-flow] Headless login:`,
`[device-flow] Pending login found`, or the AuthError message starts with
`[HEADLESS_LOGIN_ACTION]`, this means the environment has no browser and the user must
authorize on another device.

### Parsing the AuthError

The AuthError message is structured for easy parsing:

```
[HEADLESS_LOGIN_ACTION] url=<raw_url> | markdown=[Authorize in QwenCloud](<url>) | action=Present URL to user then IMMEDIATELY re-run with --poll
```

- **`url`** — Raw URL, always present. Use this if your output does not support Markdown.
- **`markdown`** — Pre-formatted Markdown link. Use this if your output supports Markdown
  so the user sees a clickable "Authorize in QwenCloud" link.
- **`action`** — What you MUST do next.

### Agent MUST follow this exact sequence:

1. **Present the URL to the user** — Use the `markdown` field if your output supports
   Markdown (renders as a clickable link). Otherwise use the raw `url` field. Tell the
   user to open it in any browser and complete authorization.
2. **IMMEDIATELY re-run the same command with `--poll`** — Append `--poll` to the original
   command arguments. Do NOT wait for the user to confirm they have authorized. The script
   will poll until the user completes authorization (up to ~15 minutes). The poll is
   blocking — it will wait and return results once authorization succeeds.
3. **If poll times out** — The script exits with code 2 again. Show the user a new URL
   and repeat from step 1.

### Example agent flow

```
Run: python3 usage.py summary --period month
→ Exit code 2, stderr contains: "[HEADLESS_LOGIN_ACTION] url=https://... | markdown=[Authorize in QwenCloud](https://...) | action=..."
→ Agent says: "Please sign in: [Authorize in QwenCloud](https://...) I'll start polling now."
→ Agent IMMEDIATELY runs: python3 usage.py summary --period month --poll
→ Script polls... user authorizes... script outputs summary results
→ Agent displays results
```

### NEVER:

- ❌ Ask the user "Have you completed authorization?" before re-running
- ❌ Wait for user confirmation before polling
- ❌ Re-run without `--poll` (this would just output the URL again and exit)
- ❌ Ignore the `action` field in the AuthError message

## Exit Codes

| Code | Meaning              |
|------|----------------------|
| 0    | Success              |
| 2    | Authentication error |
| 3    | Network/API error    |

## Update Check (MANDATORY Post-Execution)

After script execution, check stderr for action signals. The script automatically detects update status and emits
structured signals. You MUST act on them. This section also applies when the user explicitly asks to check for updates.

### Signal: `[ACTION_REQUIRED] qwencloud-update-check skill is not installed`

When stderr contains this signal, you MUST present the following options to the user and **wait for their response
before proceeding**. Do NOT silently skip this.

> The update-check skill is not installed. It keeps you informed about new qwencloud/qwencloud-ai features and bug fixes.
>
> 1) **Install now** — I'll run the install command for you
> 2) **Skip for now** — do nothing this time
> 3) **Never remind me** — permanently suppress this prompt

After the user responds:

- User chooses **1** → run:
  `npx skills add QwenCloud/qwencloud-ai --skill qwencloud-update-check -y`, then run:
  `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`
- User chooses **2** → run: `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`, then continue normally
- User chooses **3** → run: `python3 <this-skill-scripts-dir>/gossamer.py --never-install`, then continue normally

### Signal: `[UPDATE_AVAILABLE]`

When stderr contains this signal, you MUST append a brief update notice to your response, including the version info and
the update command shown in the stderr output.

### No signal in stderr

If stderr contains neither `[ACTION_REQUIRED]` nor `[UPDATE_AVAILABLE]`, no action is needed — the skill is installed
and up to date (or cached within 24h).

### Explicit user request

When the user explicitly asks to check for updates (e.g. "check for updates", "check version"):

1. Look for `qwencloud-update-check/SKILL.md` in sibling skill directories.
2. If found — run: `python3 <qwencloud-update-check-dir>/scripts/check_update.py --print-response` and report the result.
3. If not found — present the install options above.

## Implementation Notes

- **Pay-as-you-go**: API returns total usage only (no input/output split)
- **Coding Plan**: Aggregate request counts at plan level (no per-model breakdown)
- **logout**: Calls `POST t.qwencloud.com/cli/device/logout?token=<auth_token>` (token optional) with `Authorization: Bearer <access_token>`, then clears local credentials. Server-side call is best-effort — local logout always succeeds.
- **Authentication**: Uses Bearer token against `cli.qwencloud.com/data/v2/api.json` (JSON body). Headless mode is auto-detected (SSH, container, no DISPLAY, no browser).
- **Dependencies**: Python 3.9+. Run `pip install -r <path-to-skill>/scripts/requirements.txt` before first use.
