---
name: qwencloud-model-selector
description: "[QwenCloud] Recommend the best Qwen model and parameters. TRIGGER when: choosing between Qwen models, comparing Qwen model pricing, understanding Qwen model capabilities, checking usage or billing, viewing cost history, when an execution skill needs model selection advice, or user explicitly invokes this skill by name (e.g. use qwencloud-model-selector). DO NOT TRIGGER when: non-Qwen model discussions (OpenAI, Gemini, etc.), general AI questions unrelated to Qwen."
compatibility: "Advisory skill, no execution dependencies. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

> **Agent setup**: If your agent doesn't auto-load skills (e.g. Claude Code),
> see [agent-compatibility.md](references/agent-compatibility.md) once per session.

# Qwen Model Selector (Advisor)

This skill operates in two modes:

1. **Interactive advisory** — asks diagnostic questions to recommend the right model (see Diagnostic Flow).
2. **Cross-skill resolution** — provides a fast-path model lookup for execution skills that need a model
   decision without user interaction (see [recommendation-matrix.md](references/recommendation-matrix.md)).

Do not fabricate model names — only recommend models listed in this skill or returned by CLI.
This skill is part of **qwencloud/qwencloud-ai**.

## Skill directory

Load on demand. Do not fetch external URLs unless the user explicitly asks for the latest data.

| Location                                  | Purpose                                                                          |
|-------------------------------------------|----------------------------------------------------------------------------------|
| `references/cli-usage.md`                 | **CLI-first data strategy**: when to use CLI, 3-step login flow, display rules   |
| `references/error-handling.md`            | CLI error classification & recovery actions (auth, not-found, network, ...)      |
| `references/recommendation-matrix.md`     | Full model recommendation tables, Cross-Skill Resolution, Coding Plan, Thinking  |
| `references/pricing-disclaimer.md`        | Pricing guidance + **mandatory** cost-estimation disclaimer (CN/EN) + console links |
| `references/pricing.md`                   | Pricing structural overview (offline snapshot)                                   |
| `references/model-list.md`                | Model catalog (offline snapshot)                                                 |
| `references/sources.md`                   | Official documentation URLs (manual lookup only)                                 |
| `references/agent-compatibility.md`       | Agent self-check for skill registration                                          |

## Prerequisites

**QwenCloud CLI is strongly recommended** — it is the authoritative real-time data source for model
availability, pricing, and quotas. Verify with:

```bash
qwencloud version
```

If not installed:

```bash
npm install -g @qwencloud/qwencloud-cli
```

Node.js >= 18 required. Without CLI you can still answer general navigation questions from offline
snapshots, but **you cannot answer "latest", "exact price", or "specific model details" questions**.

## Security & Credential Model

QwenCloud has **two independent credential systems** — never confuse them:

| Credential | Purpose | How to provide |
|------------|---------|----------------|
| **API Key** (`sk-...` / `sk-sp-...`) | Call model APIs in your code | `$DASHSCOPE_API_KEY` / `$QWEN_API_KEY` env var |
| **CLI session** | Authorize `qwencloud` CLI subcommands | `qwencloud auth login` (browser device flow) |

**Red lines (apply to both):**

- **NEVER output any credential value in plaintext.** Use variable references; report only status
  ("set" / "not set", "valid" / "invalid"). Never display `.env` or config file contents.
- **NEVER conflate the two systems.** When CLI returns `Not authenticated` / `AUTH_REQUIRED`, run the
  3-step device-flow login (see [cli-usage.md](references/cli-usage.md#authentication-3-step-login-flow)).
  **DO NOT** ask the user for an API key, and **DO NOT** try to set `$DASHSCOPE_API_KEY` to fix CLI auth.

## Data Resolution Order

Match the user's question to the right data source. **Do not fall back to a lower tier without trying
the recovery actions in the higher tier first.**

| Question type                                                  | Primary source                                          | Notes                                                |
|----------------------------------------------------------------|---------------------------------------------------------|------------------------------------------------------|
| General navigation ("which family for text chat?")             | SKILL.md `Default` table + `recommendation-matrix.md`   | Offline-answerable                                   |
| **Latest / exact / specific** (price, model details, quota)    | **CLI MUST be used** — see `cli-usage.md`               | Snapshots are stale; never invent numbers            |
| Search by capability ("model that does X")                     | `qwencloud models search "<X>" --format json`           | Snapshot keyword coverage is incomplete              |
| CLI returned an error                                          | `error-handling.md` recovery actions, **then retry**    | Auth failure → run 3-step login, do not skip to snapshot |
| CLI completely unavailable AND user declines install/login     | `model-list.md`, `pricing.md` (with stale-data caveat)  | Only after CLI recovery genuinely failed             |
| All of the above cannot answer AND user confirms online lookup | URLs in `sources.md`                                    | Never proactively fetch                              |

## Diagnostic Flow (Interactive Advisory)

Ask the user (in order):

1. **Content type?** — text / image / video / audio / vision
2. **Primary task?** — generation / understanding / coding / reasoning / translation
3. **Priority?** — quality vs speed vs cost
4. **Input size?** — short / medium / long context
5. **Structured output?** — JSON / function calling needed?

## Default Recommendations

No clear signals → use the canonical default for the domain. For specialized cases (reasoning, coding,
OCR, role-play, image editing, etc.) and per-domain comparison, see
[recommendation-matrix.md](references/recommendation-matrix.md).

| Domain              | Default          | Quality          | Speed              | Cost               |
|---------------------|------------------|------------------|--------------------|--------------------|
| text.chat           | qwen3.6-plus     | qwen3-max        | qwen3.5-flash      | qwen-turbo         |
| vision.analyze      | qwen3.6-plus     | qwen3-vl-plus    | qwen3-vl-flash     | qwen3-vl-flash     |
| omni (voice+vision) | qwen3-omni-flash | qwen3-omni-flash | qwen3-omni-flash   | —                  |
| image.generate      | wan2.6-t2i       | wan2.6-t2i       | wan2.2-t2i-flash   | wan2.2-t2i-flash   |
| image.edit          | wan2.6-image     | wan2.6-image     | wan2.5-i2i-preview | wan2.5-i2i-preview |
| video.t2v           | wan2.6-t2v       | wan2.6-t2v       | —                  | —                  |
| video.i2v           | wan2.6-i2v-flash | wan2.6-i2v       | wan2.6-i2v-flash   | —                  |
| audio.tts           | qwen3-tts-flash  | cosyvoice-v3-plus| qwen3-tts-flash    | qwen3-tts-flash    |

> **Degradation**: If this skill is not loaded, each execution skill falls back to its own built-in
> default. This protocol is purely additive — it enhances model selection but never blocks execution.

## CLI Quick Reference

> **Auth required.** All `models` and `usage` commands need an active **CLI session** (browser
> device-flow login — **NOT** the API key). If the command returns `Not authenticated` / `AUTH_REQUIRED`:
> 1. **Run the 3-step device-flow login** in [cli-usage.md](references/cli-usage.md#authentication-3-step-login-flow)
>    (proactively open the verification URL using the OS-appropriate command, then poll immediately).
> 2. **Retry the original command** after `success`.
> 3. **DO NOT** ask the user for `$DASHSCOPE_API_KEY` / `$QWEN_API_KEY` — those are for model API
>    calls, not CLI session. See [Security & Credential Model](#security--credential-model) above.
> 4. **DO NOT** silently fall back to snapshots.

| Need                          | Command                                                            |
|-------------------------------|--------------------------------------------------------------------|
| Full model catalog            | `qwencloud models list --all --format json`                        |
| Filter by modality            | `qwencloud models list --input image --output text --format json`  |
| Single model details          | `qwencloud models info <model-id> --format json`                   |
| Keyword search                | `qwencloud models search "<query>" --format json`                  |
| Free tier remaining           | `qwencloud usage free-tier --format json`                          |
| Auth status                   | `qwencloud auth status --format json`                              |

**Display rules**: Parse `--format json` output and present a human-readable summary; never dump raw
JSON. Display `--format text` output as-is, then add analysis after `---`. See
[cli-usage.md](references/cli-usage.md#agent-display-rules-for-cli-output) for details.

## CLI Error Handling — Quick Guide

When CLI fails, **classify first, recover, then retry**. Never silently fall back to snapshots.

| Category          | Recovery (summary)                                                             |
|-------------------|--------------------------------------------------------------------------------|
| `auth-failure`    | Run 3-step login → **retry the original command**. Fall back only if user declines. |
| `not-installed`   | Show install command → ask user to install → retry. Do NOT silently use snapshot.   |
| `model-not-found` | Run `qwencloud models search "<keyword>"` → propose top 3 → retry with correct ID.  |
| `network-timeout` | Retry once after 2s; only after second failure ask whether to fall back.            |
| `rate-limit`      | Show [Rate Limit Console](https://home.qwencloud.com/settings/monitoring/rate-limit); user decides. |
| `quota-exhausted` | Show [Billing Console](https://home.qwencloud.com/billing/pay-as-you-go); do NOT use snapshot. |
| `version-mismatch`| Suggest `qwencloud version --check` or update-check skill → upgrade → retry.        |
| `other`           | Show raw stderr; link to docs; only after user opt-out, fall back.                  |

Full classification, signals, and example flows: [error-handling.md](references/error-handling.md).

## Pricing & Cost Estimation

- **Latest pricing**: Run `qwencloud models info <model> --format json` first; use `pricing.md` only as
  offline fallback. **Never invent a price.**
- **Mandatory disclaimer**: Every cost-related answer **must** end with the disclaimer in
  [pricing-disclaimer.md](references/pricing-disclaimer.md) (Chinese or English version, matching the
  user's response language). Omitting the disclaimer is a **critical failure**.
- **Free quota**: Never assume free quota is available — use `qwencloud usage free-tier` to verify or
  direct the user to the [console](https://home.qwencloud.com/benefits).
- **Usage / billing queries**: Direct the user to the appropriate console page — see the table in
  [pricing-disclaimer.md](references/pricing-disclaimer.md#usage--billing-console).

## Update Check

When the user asks to check for updates ("check for updates", "check version", "is there a new version",
"update skills"):

1. **Find qwencloud-update-check**: Look for `qwencloud-update-check/SKILL.md` in sibling skill directories.
2. **If found** — run: `python3 <qwencloud-update-check-dir>/scripts/check_update.py --print-response`
   and report the result. Use `--force` if the user asks to force-check.
3. **If not found** — run `qwencloud version --check` and report the result.

## Anti-Patterns

- **Never fabricate model names** — only recommend models listed in this skill or returned by CLI.
- **Never invent or guess any price figure** — use CLI / `pricing.md` / official pricing page only.
  Fabricating a price is a **critical failure**.
- **Never silently fall back to snapshots when CLI errors out** — apply
  [error-handling.md](references/error-handling.md) recovery actions first.
- **Never assume free quota is available** — quotas may have been consumed, expired, or removed. Always
  present the paid unit price first.
- **Never output API keys in plaintext** — see Security section.
- **Never confuse CLI session with API key** — CLI auth uses browser device-flow login; never offer
  `$DASHSCOPE_API_KEY` or `$QWEN_API_KEY` as a fix for CLI `Not authenticated` / `AUTH_REQUIRED` errors.
- **Never proactively fetch URLs or trigger web searches** — only access online sources when CLI +
  snapshots cannot answer AND the user confirms.
- **Never construct usage/billing/console URLs** — only use the exact links listed in this skill or its
  references. If a URL is not listed, do not invent one.
- **Always include the cost disclaimer** for any cost-related answer (see
  [pricing-disclaimer.md](references/pricing-disclaimer.md)).

## References

| Source                                                       | Purpose                                                          |
|--------------------------------------------------------------|------------------------------------------------------------------|
| [cli-usage.md](references/cli-usage.md)                      | CLI-first strategy, 3-step login, display rules, model detail URL |
| [error-handling.md](references/error-handling.md)            | CLI error classification & recovery                              |
| [recommendation-matrix.md](references/recommendation-matrix.md) | Full recommendation tables, Cross-Skill Resolution, Coding Plan, Thinking Mode |
| [pricing-disclaimer.md](references/pricing-disclaimer.md)    | Pricing guidance + mandatory disclaimer + billing console links  |
| [pricing.md](references/pricing.md)                          | Pricing structural overview (offline snapshot)                   |
| [model-list.md](references/model-list.md)                    | Model catalog (offline snapshot)                                 |
| [sources.md](references/sources.md)                          | Official documentation URLs                                      |
| [agent-compatibility.md](references/agent-compatibility.md)  | Agent self-check for skill registration                          |
| `qwencloud models list --format json`                        | Dynamic: full model catalog with pricing, features, quotas       |
| `qwencloud models info <id> --format json`                   | Dynamic: single model details (pricing tiers, context, rate limits) |
| `qwencloud models search "<q>" --format json`                | Dynamic: keyword-based model discovery                           |
| `qwencloud usage free-tier --format json`                    | Dynamic: remaining free tier quota per model                     |
