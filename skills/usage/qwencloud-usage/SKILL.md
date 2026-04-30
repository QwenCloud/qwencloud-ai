---
name: qwencloud-usage
description: "[QwenCloud] Manage account auth and query usage/billing. Use for: login, logout, check usage, view billing, free tier quota, coding plan status, pay-as-you-go costs. Skip for: model browsing, non-account tasks."
---

# QwenCloud Usage

Query QwenCloud usage, free tier quota, coding plan status, and pay-as-you-go billing.

## Prerequisites

- **QwenCloud CLI** must be installed. Verify with:

```bash
qwencloud version
```

If not installed, run:

```bash
npm install -g @qwencloud/qwencloud-cli
```

Node.js >= 18 required.

- Authentication: No configuration needed on first use. The CLI handles non-TTY detection and safe login automatically (see Authentication Flow below).

### Environment Variables

| Variable                    | Description                                                                                  |
|-----------------------------|----------------------------------------------------------------------------------------------|
| `QWENCLOUD_KEYRING`         | Set to `plaintext`, `no`, `0`, `false`, or `off` to opt out of OS keychain credential storage. |
| `QWENCLOUD_CREDENTIALS_DIR` | Override file-based credential directory (default: `~/.qwencloud/credentials`).              |

## Authentication Flow (for Agents)

The CLI auto-detects non-TTY environments and degrades safely — no wrapper script needed.

### TL;DR — 3-step auth path

1. `qwencloud auth status --format json` → `authenticated: true` → skip to commands
2. `qwencloud auth login --init-only --format json` → extract `verification_url` → open in browser
3. `qwencloud auth login --complete --format json` → poll until `success` event

### Quick check: already logged in?

```bash
qwencloud auth status --format json
```

If `authenticated: true` and token is not expired, skip login entirely.

### Recommended: Two-phase login

Works in all environments (desktop, headless, remote container).

**Step 1 — Initialize login (non-blocking):**
```bash
qwencloud auth login --init-only --format json
```
Exits immediately. Parse the stdout JSON `events` array:
- `already_authenticated` → user is logged in, skip to commands
- `device_code` → extract `verification_url` and present it to the user

On desktop environments with a browser, open the URL for the user:
```bash
open "$VERIFICATION_URL"          # macOS
xdg-open "$VERIFICATION_URL"      # Linux
start "" "$VERIFICATION_URL"      # Windows
```

**Step 2 — IMMEDIATELY start polling (do NOT wait for user confirmation):**
```bash
qwencloud auth login --complete --format json
```
Parse the stdout JSON `events` array:
- `success` → login complete, proceed to commands
- `expired` → device code expired, go back to Step 1
- `error` → report failure

### TTY environments (interactive terminal)

If the agent is running in a TTY (e.g., user's terminal), simply run:
```bash
qwencloud auth login
```
The CLI will automatically open the browser and poll until authorization completes.

### JSON event structure

Both `--init-only` and `--complete` output a single JSON document:
```json
{
  "events": [
    {"event": "device_code", "verification_url": "...", "expires_in": 300},
    {"event": "success", "authenticated": true, "user": {"aliyunId": "..."}}
  ]
}
```

Event types: `already_authenticated`, `device_code`, `success`, `expired`, `error`, `pending`.

### NEVER:

- ❌ Ask the user "Have you completed authorization?" before running `--complete`
- ❌ Wait for user confirmation before polling — run `--complete` immediately after presenting the URL
- ❌ Re-run `--init-only` without completing (this creates a new device code and invalidates the previous one)

## Usage

All commands support `--format json` for structured, machine-parseable output (**recommended default**), and `--format text` for clean plaintext output.

For agent use, **always prefer `--format json`** and parse the JSON response. Only fall back to `--format text` when the user explicitly requests human-readable plaintext.

Never parse `table` format programmatically — it contains ANSI codes and Unicode borders.

### Auth Commands

**`qwencloud auth status`** — Check current authentication state

```bash
qwencloud auth status --format json
```

**`qwencloud auth logout`** — Revoke session server-side and clear local credentials

```bash
qwencloud auth logout
```

### Usage Commands

**`qwencloud usage summary`** — View usage summary (free tier, coding plan, pay-as-you-go)

```bash
qwencloud usage summary                      # Current month
qwencloud usage summary --period last-month  # Last month
qwencloud usage summary --from 2026-03-01 --to 2026-03-31
qwencloud usage summary --format json        # JSON output
```

**Period presets**: `today`, `yesterday`, `week`, `month` (default), `last-month`, `quarter`, `year`, `YYYY-MM`

**`qwencloud usage breakdown`** — View model usage breakdown

```bash
qwencloud usage breakdown --model qwen3.6-plus --days 7
qwencloud usage breakdown --model qwen3.5-plus --period 2026-03
qwencloud usage breakdown --model qwen-plus --period 2026-03 --granularity month
qwencloud usage breakdown --model qwen3.6-plus --format json
```

**`qwencloud usage free-tier`** — View free tier quota details

```bash
qwencloud usage free-tier
qwencloud usage free-tier --format json
```

**`qwencloud usage payg`** — View pay-as-you-go billing details

```bash
qwencloud usage payg
qwencloud usage payg --format json
```

### Breakdown Parameters: How to Think About Them

**Three independent dimensions — combine them freely:**

`--model` (required) + **date range** + **granularity**

**Model scope:**
- `--model <id>` — single model (e.g. `qwen3.5-plus`); **required** for breakdown

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

**Classic examples:**
```bash
# Single model, single month, daily detail
qwencloud usage breakdown --model qwen3.5-plus --period 2026-03

# Single model, last 3 months, monthly summary
qwencloud usage breakdown --model qwen3.5-plus --days 90 --granularity month

# Single model, specific quarter, quarterly rollup
qwencloud usage breakdown --model qwen3.5-plus --from 2026-01-01 --to 2026-03-31 --granularity quarter

# Single model, this month, daily breakdown
qwencloud usage breakdown --model qwen3.6-plus --period month
```

## Output and Agent Display Rules

CLI commands return JSON by default in agent/pipe environments (`auto` format: TTY → table, pipe → json).
**JSON is the primary output mode for agents** — always pass `--format json` explicitly, parse the structured response, then present a human-readable summary to the user.

### JSON output example (`--format json`)

```bash
qwencloud usage summary --period month --format json
```

Returns structured JSON with three sections:
```json
{
  "period": { "from": "2026-04-01", "to": "2026-04-24" },
  "free_tier": [
    { "model_id": "qwen3.6-plus", "quota": { "remaining": 850000, "total": 1000000, "unit": "tokens", "used_pct": 15 } }
  ],
  "coding_plan": {
    "subscribed": true,
    "plan": "PRO",
    "windows": {
      "per_5h": { "remaining": 4800, "total": 6000, "used_pct": 20 },
      "weekly": { "remaining": 38200, "total": 45000, "used_pct": 15 },
      "monthly": { "remaining": 82500, "total": 90000, "used_pct": 8 }
    }
  },
  "pay_as_you_go": {
    "models": [
      { "model_id": "qwen3.6-plus", "usage": { "tokens_total": 480000 }, "cost": 0.38, "currency": "USD" },
      { "model_id": "qwen-plus", "usage": { "tokens_total": 460000 }, "cost": 0.13, "currency": "USD" }
    ],
    "total": { "cost": 0.51, "currency": "USD" }
  }
}
```

### Text output example (`--format text`)

```bash
qwencloud usage summary --period month --format text
```

```plaintext
Usage Summary  ·  2026-04-10

-- Free Tier Quota -------------------------------------------------------
Model                Remaining      Total          Progress
qwen3.6-plus         850K tokens    1M tokens      85% left
wan2.6-t2i           38 images      50 images      76% left
--------------------------------------------------------------------------

-- Coding Plan · PRO Plan ------------------------------------------------
Window           Remaining      Total          Progress
Per 5 hours      4.8K req       6K req         20% used
This week        38.2K req      45K req        15% used
This month       82.5K req      90K req         8% used
--------------------------------------------------------------------------

-- Pay-as-you-go · 2026-04-01 → 2026-04-10 -------------------------------
Model                Usage              Cost
qwen3.6-plus         480K tok           $0.38
qwen-plus            460K tok           $0.13
--------------------------------------------------------------------------
Total                —                  $0.51
```

### ⚠️ CRITICAL: How to present output to the user

**When using `--format json` (recommended for agents):**

1. **Parse the JSON** and extract the relevant data for the user's question
2. **Present a human-readable summary** — do not dump raw JSON to the user
3. **Add analysis AFTER the summary** — clearly separated with `---`

**When using `--format text`:**

1. **Display CLI output EXACTLY AS-IS** — no modification, no reformatting
2. **Preserve all formatting** — alignment, spacing, progress bars, separators
3. **Add analysis AFTER output only** — clearly separated with `---`

**NEVER:**
- ❌ Dump raw JSON to the user without interpretation
- ❌ Reformat or summarize text/table output
- ❌ Add prefixes like "Here's your usage:"
- ❌ Convert text/table output to bullet points

**✅ CORRECT (JSON mode):**
```
Your QwenCloud usage for April:

**Free Tier**: qwen3.6-plus has 85% remaining (850K / 1M tokens), wan2.6-t2i has 76% remaining (38 / 50 images).
**Coding Plan (PRO)**: 8% used this month (82.5K / 90K requests).
**Pay-as-you-go**: $0.51 total — qwen3.6-plus $0.38, qwen-plus $0.13.

---

**💡 Analysis**: Your qwen3.6-plus free tier is 85% remaining...
```

**✅ CORRECT (Text mode):**
```
[CLI text output - exactly as-is]

---

**💡 Analysis**: Your qwen3.6-plus free tier is 85% remaining...
```

**❌ WRONG:**
```
Here's your usage:
- qwen3.6-plus: 850K tokens remaining (85% left)
```

## Exit Codes

| Code | Meaning              |
|------|----------------------|
| 0    | Success              |
| 1    | General/usage error  |
| 2    | Authentication error |
| 3    | Network error        |
| 4    | Configuration error  |
| 130  | Interrupted          |

## CLI Update Check

When the user explicitly asks to check for cli updates (e.g. "check for cli updates", "check cli version", "is there a new version cli"):

1. Run: `qwencloud version --check`
2. Report the result.

The QwenCloud CLI handles update notifications natively; no additional stderr signal handling is required in this skill.

## Implementation Notes

- **Pay-as-you-go**: API returns total usage only (no input/output split)
- **Coding Plan**: Aggregate request counts at plan level (no per-model breakdown)
- **logout**: Revokes server-side session and clears local credentials (keychain + file). Server-side call is best-effort — local logout always succeeds.
- **Authentication**: Uses OAuth 2.0 Device Authorization Grant with PKCE. Credentials stored in OS keychain when available, with encrypted file fallback.
- **breakdown --model is required**: Unlike the previous Python implementation, the CLI requires `--model` for breakdown. To query all models' usage, use `qwencloud usage summary` instead.
