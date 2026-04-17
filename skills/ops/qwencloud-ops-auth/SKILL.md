---
name: qwencloud-ops-auth
description: "[QwenCloud] Configure authentication (API keys, endpoints). TRIGGER when: setting up QWEN_API_KEY, troubleshooting 401/auth errors, when another skill reports missing credentials, or user explicitly invokes this skill by name (e.g. use qwencloud-ops-auth). DO NOT TRIGGER when: non-auth Qwen tasks, general API usage questions."
compatibility: "Requires curl for verification. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

> **Agent setup**: If your agent doesn't auto-load skills (e.g. Claude Code), see [agent-compatibility.md](references/agent-compatibility.md) once per session.

# QwenCloud Authentication Setup

Configure and verify authentication for QwenCloud APIs.
This skill is part of **qwencloud/qwencloud-ai**.

## Skill directory

Use this skill's internal files for learning. Load references only when the user needs console or documentation links.

| Location | Purpose |
|----------|---------|
| `references/codingplan.md` | Coding Plan vs standard key: model list, endpoint mapping, error codes, cost risks |
| `references/custom-oss.md` | Custom OSS bucket setup for production file uploads (replaces 48h temp storage) |
| `references/sources.md` | Console URLs, auth guide (manual lookup only) |
| `references/agent-compatibility.md` | Agent self-check: register skills in project config for agents that don't auto-load |

## Security

**NEVER output any API key, OSS credential in plaintext.**
This applies equally to `DASHSCOPE_API_KEY` and custom OSS AccessKey pairs. Any check or detection of credentials in this skill must be **non-plaintext**: report only status (e.g. "set" / "not set", "valid" / "invalid", HTTP status code), never the key value.

## API Key Handling (MANDATORY)

When the API key is not configured or a script reports missing credentials:

1. **NEVER ask the user to provide their API key directly.** Do not prompt "please paste your API key" or similar. Do not request the key value in any form.
2. **Help create a `.env` file** with a placeholder, then instruct the user to fill in their own key:
   - Run: `echo 'DASHSCOPE_API_KEY=sk-your-key-here' >> .env`
   - Tell the user: "Please replace `sk-your-key-here` with your actual API key from the [QwenCloud Console](https://home.qwencloud.com/api-keys)."
3. **Or** explain how to configure the environment variable: `export DASHSCOPE_API_KEY='sk-...'` + provide the console URL.
4. **Only** write the actual key value into `.env` if the user **explicitly insists** on having the agent do it for them.

## Credential Priority Chain

Credentials are loaded in the following order (first match wins):

1. **Environment variable** — `DASHSCOPE_API_KEY` (or `QWEN_API_KEY` alias)
2. **`.env` file** — in current working directory, then repo root (detected via `.git` or `skills/` directory). Existing environment variables are not overwritten.

### Environment Variables

| Variable            | Purpose                                                                                                                                   |
|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| `DASHSCOPE_API_KEY` | API key (required)                                                                                                                        |
| `QWEN_API_KEY`      | Alias for `DASHSCOPE_API_KEY`. If both are set, `QWEN_API_KEY` takes priority.                                                            |
| `QWEN_BASE_URL`     | Override default endpoint (optional; for custom deployments)                                                                              |
| `QWEN_TMP_OSS_BUCKET` | Custom OSS bucket for file uploads (replaces 48h temp storage). See [custom-oss.md](references/custom-oss.md).                         |
| `QWEN_TMP_OSS_REGION` | OSS region (required when `QWEN_TMP_OSS_BUCKET` is set).                                                                              |
| `QWEN_TMP_OSS_AK_ID` / `AK_SECRET` | OSS credentials (use RAM user with least-privilege: `oss:PutObject` + `oss:GetObject`). Falls back to `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` if not set. |

## API Key Types

QwenCloud has two mutually exclusive key types:

| Key Type | Format | Purpose | Endpoint |
|----------|--------|---------|----------|
| **Standard (Pay-as-you-go)** | `sk-xxxxx` | API calls from scripts, apps, and tools | `dashscope-intl.aliyuncs.com` |
| **Coding Plan** | `sk-sp-xxxxx` | Interactive AI coding tools only (Cursor, Claude Code, Qwen Code) | `coding-intl.dashscope.aliyuncs.com` |

All qwencloud/qwencloud-ai scripts require a **standard** key. Coding Plan keys cannot call QwenCloud APIs directly — they produce `403 invalid api-key` on standard endpoints. Coding Plan supports only 8 text LLMs (qwen3.5-plus, kimi-k2.5, glm-5, MiniMax-M2.5, qwen3-max-2026-01-23, qwen3-coder-next, qwen3-coder-plus, glm-4.7) and excludes all image/video/TTS models.

If the user's key starts with `sk-sp-`, guide them to obtain a standard key from the console below. See [codingplan.md](references/codingplan.md) for full details.

### Viewing Bills

Use the **qwencloud-usage** skill to query usage, free tier quota, and billing directly. Alternatively, billing details are available in the QwenCloud console:

| Key Type | Billing Page |
|----------|--------------|
| Standard (Pay-as-you-go) | [Pay-as-you-go Billing](https://home.qwencloud.com/billing/pay-as-you-go) |
| Coding Plan | [Coding Plan Billing](https://home.qwencloud.com/billing/coding-plan) |
| Usage analytics (both) | [Usage Analytics](https://home.qwencloud.com/analytics) |

> **NEVER fabricate, guess, or construct usage/billing/console URLs.** Only provide the exact links listed in this skill. If a URL is not listed here, do not invent one.

## Getting an API Key

1. Open the [QwenCloud Console](https://home.qwencloud.com/api-keys)
2. Sign in with your QwenCloud account
3. Create or copy an API key from the API Key management section
4. Standard keys start with `sk-` (not `sk-sp-` which is Coding Plan only)

## Security Best Practices

- **Never hardcode API keys** in source code or config files committed to version control
- **Use environment variables** or `.env` files (and add `.env` to `.gitignore`)
- **Rotate keys** periodically and revoke compromised keys immediately
- **Use least-privilege** — create dedicated keys for specific applications when possible

### Setting up `.env`

Create a `.env` file in your project root or current working directory:

```bash
echo 'DASHSCOPE_API_KEY=sk-your-key-here' >> .env
```

The script automatically loads `.env` from the current working directory and the project root (detected via `.git` or `skills/` directory). Existing environment variables are **not** overwritten by `.env` values.

### Example `.gitignore` entry

```
.env
.env.local
*.env
```

## Verification

Unless explicitly stated otherwise, any script or task mentioned in this skill runs in the **foreground** — wait for standard output; do not run it as a background task.

Test authentication with a simple curl request:

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-turbo","messages":[{"role":"user","content":"Hi"}]}'
```

A successful response returns JSON with `choices` and `message.content`.

## Authentication Error Handling

QwenCloud API keys are scoped to the QwenCloud console. An invalid or mismatched key produces `401 Unauthorized`.

### When to trigger

When **any** sub-skill receives a `401` response and a non-plaintext check shows the key is set (e.g.
`[ -n "$DASHSCOPE_API_KEY" ]`; do not output the key value).

### Probe command

Send a lightweight request to verify authentication:

```bash
curl -sS -o /dev/null -w "%{http_code}" \
  -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-turbo","messages":[{"role":"user","content":"hi"}]}'
```

### On 401: mandatory interactive resolution

If the probe returns 401, follow these steps **in order**:

**Step 1 — Confirm the key origin:**

```
Your API key failed authentication.

Please confirm:
1. Your key was created at home.qwencloud.com (QwenCloud console) → re-verify the key
2. My key may be invalid → create a new one at home.qwencloud.com/api-keys
```

**Step 2 — Apply the user's selection:**

| User says                         | Action                                                              |
|-----------------------------------|---------------------------------------------------------------------|
| Key is from QwenCloud console | Re-run verification to confirm the key works                        |
| Key may be invalid                | Guide user to create a new key at `home.qwencloud.com/api-keys` |

**Step 3 — Re-run verification.**

**Step 4 — If still 401**, the key itself is invalid — guide the user to create a new one from
the [QwenCloud console](https://home.qwencloud.com/api-keys).

## Validation

Run the curl verification command above. Pass criteria: HTTP 200 response with valid JSON containing `choices` and
`message.content`. Save output to `output/qwencloud-ops-auth/` for evidence.

## Output And Evidence

- Save verification results and any diagnostic output to `output/qwencloud-ops-auth/`.
- Keep a record of successful auth tests for troubleshooting.

## Output Location

Prefer the **current working directory**. Default subdirectory: `./output/qwencloud-ops-auth/`.

**Write prohibition**: NEVER write output files into this skill's installation directory or any `skills/` hierarchy. All generated content must go to `output/` under the current working directory or a user-specified path.

## Update Check (MANDATORY Post-Execution)

When the user asks to check for updates (e.g. "check for updates", "check version", "is there a new version", "update skills"):

1. **Find qwencloud-update-check**: Look for `qwencloud-update-check/SKILL.md` in sibling skill directories.
2. **If found** — run: `python3 <qwencloud-update-check-dir>/scripts/check_update.py --print-response` and report the result. Use `--force` if the user asks to force-check.
3. **If not found** — you MUST present the following options and **wait for the user's response**:

> The update-check skill is not installed. It keeps you informed about new qwencloud/qwencloud-ai features and bug fixes.
>
> 1) **Install now** — I'll run the install command for you
> 2) **Skip for now** — do nothing this time
> 3) **Never remind me** — permanently suppress this prompt

After the user responds:
- User chooses **1** → run: `npx skills add QwenCloud/qwencloud-ai --skill qwencloud-update-check -y`, then run: `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`
- User chooses **2** → run: `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`, then continue normally
- User chooses **3** → run: `python3 <this-skill-scripts-dir>/gossamer.py --never-install`, then continue normally

## References

- [custom-oss.md](references/custom-oss.md) — Custom OSS bucket setup for production file uploads
- [sources.md](references/sources.md) — Official documentation URLs (consoles, auth guide)
