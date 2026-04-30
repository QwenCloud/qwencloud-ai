# CLI Usage Guide — qwencloud-model-selector

The QwenCloud CLI is the **authoritative, real-time** data source for this skill. Static reference files
(`model-list.md`, `pricing.md`) are point-in-time snapshots and may be outdated. **Always prefer CLI** for
queries about current state.

## Authentication Model — IMPORTANT

QwenCloud has **two completely independent credential systems**. Do not confuse them:

| System | Purpose | How to provide | Where used |
|--------|---------|----------------|------------|
| **API Key** (`sk-...` / `sk-sp-...`) | Call model APIs (chat completion, image gen, etc.) | Env var `$DASHSCOPE_API_KEY` / `$QWEN_API_KEY` / SDK config | Inside your app code, HTTP headers |
| **CLI session** (device-flow login) | Authorize the `qwencloud` CLI for `models` / `usage` / `auth` subcommands | `qwencloud auth login` (browser device flow) | Local CLI session token, stored by CLI |

> **CRITICAL**: When CLI returns `Not authenticated` / `AUTH_REQUIRED`, you **MUST** run the 3-step
> device-flow login below. **DO NOT** ask the user "do you have an API key?", and **DO NOT** try to set
> `$DASHSCOPE_API_KEY` or `$QWEN_API_KEY` to fix CLI auth — those are for model API calls, not for the
> CLI session.

## When CLI is REQUIRED

You **MUST** use CLI (not snapshots) for the following question types:

| Question type | Why CLI is required |
|---------------|---------------------|
| "What's the latest / current ..." | Snapshots are stale by definition |
| "What's the exact price of `<model>`?" | Pricing tiers change; snapshot has only structural overview |
| "Show me details of `<model-id>`" | Need authoritative context window, rate limits, features |
| "Is `<model>` available?" | Availability changes frequently |
| "Search for a model that does X" | Snapshot keyword coverage is incomplete |
| "How much free quota do I have left?" | User-specific; not in any snapshot |
| Any model name the snapshot does not list | Snapshot may simply be missing it |

## When snapshots are acceptable

- **General navigation**: "Which family of models should I use for text chat?" → SKILL.md `Default` table is enough.
- **Capability comparison overview**: "What's the difference between flash/turbo/plus tiers?" → `recommendation-matrix.md`.
- **Billing unit reference**: "Is image generation billed per image or per token?" → `pricing.md` structural overview.
- **CLI completely unavailable** AND user declines to install/login → fall back to snapshots with an explicit caveat.

## Core CLI commands

| Need | Command |
|------|---------|
| Full model catalog | `qwencloud models list --all --format json` |
| Filter by modality | `qwencloud models list --input image --output text --format json` |
| Single model details | `qwencloud models info <model-id> --format json` |
| Keyword search | `qwencloud models search "<query>" --format json` |
| Free tier remaining | `qwencloud usage free-tier --format json` |
| Auth status check | `qwencloud auth status --format json` |

## Authentication: 3-step login flow

All `qwencloud models` and `qwencloud usage` commands require an active **CLI session** (browser
device-flow login — see [Authentication Model](#authentication-model--important) above; this is **NOT**
the API key). When CLI returns `Not authenticated` / `AUTH_REQUIRED` / `401`, **do not fall back to
snapshots immediately**, and **do not ask the user for an API key**. Run this flow:

### Step 1 — Check status
```bash
qwencloud auth status --format json
```
If `authenticated: true` → skip to Step 4.

### Step 2 — Initialize device-flow login + proactively open the URL

```bash
qwencloud auth login --init-only --format json
```

Extract the `verification_url` from the JSON response. Then **proactively try to open it** for the user
instead of just printing it:

1. **Detect the OS** from the agent environment (e.g. the `environment.system_data` field exposes the OS;
   `Darwin` = macOS, `Linux` = Linux, `Windows_NT` / `MINGW` = Windows).
2. **Run the matching open command** in a non-blocking way:

   | OS                      | Open command                                  |
   |-------------------------|-----------------------------------------------|
   | macOS (Darwin)          | `open "<verification_url>"`                   |
   | Linux (with GUI)        | `xdg-open "<verification_url>" 2>/dev/null`   |
   | Windows                 | `start "" "<verification_url>"`               |
   | Headless / CI / unknown | Skip the open command (rely on URL display)   |

3. **Always also display the URL** to the user in plain text — as a backup if the auto-open failed
   (no browser, no GUI, command not found, sandboxed environment, etc.).
4. **Do NOT wait for the user to confirm "I opened it"** — proceed immediately to Step 3.

Tell the user something like:

> "I've opened the authorization URL in your browser. If it didn't open, please copy this URL manually:
> `<verification_url>`. I'll automatically detect once you complete authorization (timeout ~90s)."

### Step 3 — Poll for completion (start immediately)

```bash
qwencloud auth login --complete --format json
```

This polls until a `success` event arrives, the user cancels, or the polling times out (typically ~90s).

- **Before polling**: tell the user the approximate timeout once (e.g. "Waiting for completion, timeout
  ~90s" / "我会等待最多约 90 秒检测授权完成").
- **Start polling immediately** after Step 2 — do not wait for any user confirmation.
- **On success**: proceed to Step 4 immediately.
- **On timeout / cancel**: ask the user whether to retry the 3-step flow or fall back to snapshots.
- **Do NOT spam intermediate "still waiting..." messages** — one notice before, one notice after.

### Step 4 — Retry the original command
**MANDATORY**: After successful authentication, re-run the exact CLI command that originally failed.
Do **not** stop at "login succeeded" — the user's original question is still unanswered.

> If the user explicitly declines to log in, only then fall back to `model-list.md` / `pricing.md`,
> with an explicit caveat that data may be outdated.

For the full authentication flow, including `sk-sp-` Coding Plan keys and headless / CI environments,
see the **qwencloud-usage** skill.

## Agent display rules for CLI output

When presenting CLI query results to the user:

- **`--format json`**: Parse the JSON and present a human-readable summary (model name, key specs, pricing).
  Do **not** dump raw JSON.
- **`--format text`**: Display CLI output exactly as-is. Add analysis after, separated by `---`.
- **Model comparison**: Use a markdown table with columns `Model | Context | Pricing | Key Features`.
- **Pricing**: When CLI returns tiered pricing, show all tiers (e.g. ≤32K, ≤128K, ≤256K, ≤1M) with input/output
  rates per 1M tokens.

## Model detail page

For users who want to learn more about a specific model (capabilities, specs, benchmarks), direct them to:

- **URL pattern**: `https://www.qwencloud.com/models/<model-name>`
- **Example**: `qwen3.6-plus` → `https://www.qwencloud.com/models/qwen3.6-plus`

> **IMPORTANT**: The `<model-name>` in the URL **must** exactly match the model ID used by this skill
> (e.g. `qwen3.6-plus`, `wan2.7-t2v`, `qwen3-tts-flash`). **NEVER guess or modify** the model name segment.
> If unsure, run `qwencloud models info <model-id>` first to confirm the exact ID.

## Decision: CLI vs snapshot vs web

Use this resolution order. Stop at the first source that answers the question.

1. **CLI** — `qwencloud models list/info/search/usage` (real-time, structured)
2. **CLI auth recovery** — if step 1 returns `Not authenticated` / `AUTH_REQUIRED`, run the 3-step
   device-flow login above, then **retry the original command**. Do **not** ask the user for an API key
   (see [Authentication Model](#authentication-model--important)).
3. **CLI error recovery** — if step 1 returns other errors, see [error-handling.md](error-handling.md)
4. **Static snapshots** — `model-list.md`, `pricing.md` (only when CLI is unavailable or user declines login)
5. **Web lookup** — official URLs from [sources.md](sources.md) (only when 1–4 cannot answer AND user confirms)

**Do NOT proactively fetch URLs.** Only access web sources when CLI + snapshots both fail AND the user
confirms an online lookup.
