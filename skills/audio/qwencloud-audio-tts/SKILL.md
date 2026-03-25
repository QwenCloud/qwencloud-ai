---
name: qwencloud-audio-tts
description: "[QwenCloud] Synthesize speech from text with Qwen TTS models. TRIGGER when: user wants to convert text to speech, create voiceovers, generate audio narration, read text aloud, build TTS applications, mentions speech synthesis/voice generation/audio output from text, or explicitly invokes this skill by name (e.g. use qwencloud-audio-tts). DO NOT TRIGGER when: user wants speech recognition/ASR, text generation without audio, non-Qwen audio tasks."
compatibility: "Requires Python 3.9+ and curl. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

> **Agent setup**: If your agent doesn't auto-load skills (e.g. Claude Code),
> see [agent-compatibility.md](references/agent-compatibility.md) once per session.

# Qwen Audio TTS (Text-to-Speech)

Synthesize natural speech from text using Qwen TTS models.
This skill is part of **qwencloud/qwencloud-ai**.

## Skill directory

Use this skill's internal files to execute and learn. Load reference files on demand when the default path fails or you need details.

| Location | Purpose |
|----------|---------|
| `scripts/tts.py` | Qwen TTS (HTTP API) — qwen3-tts-flash, qwen3-tts-instruct-flash |
| `scripts/tts_cosyvoice.py` | CosyVoice (WebSocket API) — requires `dashscope` SDK |
| `references/cosyvoice-guide.md` | CosyVoice setup, voices, examples, errors |
| `references/execution-guide.md` | Fallback: curl (standard, instruct, streaming), code generation |
| `references/prompt-guide.md` | Text formatting for speech, instructions templates, voice selection |
| `references/api-guide.md` | API supplement |
| `references/sources.md` | Official documentation URLs |
| `references/agent-compatibility.md` | Agent self-check: register skills in project config for agents that don't auto-load |

## Security

**NEVER output any API key or credential in plaintext.** Always use variable references (`$DASHSCOPE_API_KEY` in shell, `os.environ["DASHSCOPE_API_KEY"]` in Python). Any check or detection of credentials must be **non-plaintext**: report only status (e.g. "set" / "not set", "valid" / "invalid"), never the value. Never display contents of `.env` or config files that may contain secrets.

**When the API key is not configured, NEVER ask the user to provide it directly.** Instead, help create a `.env` file with a placeholder (`DASHSCOPE_API_KEY=sk-your-key-here`) and instruct the user to replace it with their actual key from the [QwenCloud Console](https://home.qwencloud.com/api-keys). Only write the actual key value if the user explicitly requests it.

## Key Compatibility

Scripts require a **standard QwenCloud API key** (`sk-...`). Coding Plan keys (`sk-sp-...`) cannot be used — TTS models are not available on Coding Plan, and Coding Plan does not support the native QwenCloud API. The script detects `sk-sp-` keys at startup and prints a warning. If qwencloud-ops-auth is installed, see its `references/codingplan.md` for full details.

## Model Selection

### Qwen TTS (HTTP API) — use `scripts/tts.py`

| Model | Use Case | Notes |
|-------|----------|-------|
| `qwen3-tts-flash` | **Recommended** (standard) — fast, multi-language | Cost-effective, widely available |
| `qwen3-tts-instruct-flash` | Instruction-guided style control | Tone/emotion via instructions |

### CosyVoice (WebSocket API) — use `scripts/tts_cosyvoice.py`

| Model | Use Case |
|-------|----------|
| `cosyvoice-v3-flash` | High quality, fast |
| `cosyvoice-v3-plus` | Highest quality |

> **Note**: CosyVoice requires `dashscope` SDK and uses different voices. See [cosyvoice-guide.md](references/cosyvoice-guide.md).

1. **User specified a model** → use the appropriate script:
   - `qwen3-tts-*` → `scripts/tts.py`
   - `cosyvoice-*` → `scripts/tts_cosyvoice.py`
2. **Consult the qwencloud-model-selector skill** when model choice depends on capability, scenario, or pricing.
3. **No signal, clear task** → `qwen3-tts-flash` via `tts.py` (default for standard tasks).

> **⚠️ Important**: The model list above is a **point-in-time snapshot** and may be outdated. Model availability
> changes frequently. **Always check the [official model list](https://www.qwencloud.com/models)
> for the authoritative, up-to-date catalog before making model decisions.**

## Available Voices

| Voice | Description | Script |
|-------|-------------|--------|
| Cherry, Ethan, Serena | Qwen TTS system voices | `tts.py` |
| longanyang, longanhuan, longhuhu_v3 | CosyVoice verified voices | `tts_cosyvoice.py` |

> **Full lists**: [api-guide.md](references/api-guide.md#system-voice-list) (Qwen TTS) · [cosyvoice-guide.md](references/cosyvoice-guide.md) (CosyVoice)

## Execution

> **⚠️ Multiple artifacts**: When generating multiple files in a single session, you MUST append a numeric suffix to each filename (e.g. `out_1.wav`, `out_2.wav`) to prevent overwrites.

### Qwen TTS (HTTP API) — `tts.py`

#### Prerequisites

- **API Key**: Check that `DASHSCOPE_API_KEY` (or `QWEN_API_KEY`) is set using a **non-plaintext** check only (e.g. in shell: `[ -n "$DASHSCOPE_API_KEY" ]`; report only "set" or "not set", never the key value). If not set: run the **qwencloud-ops-auth** skill if available; otherwise guide the user to obtain a key from [QwenCloud Console](https://home.qwencloud.com/api-keys) and set it via `.env` file (`echo 'DASHSCOPE_API_KEY=sk-your-key-here' >> .env` in project root or current directory) or environment variable. The script searches for `.env` in the current working directory and the project root. Skills may be installed independently — do not assume qwencloud-ops-auth is present.
- Python 3.9+ (stdlib only, **no pip install needed**)

#### Environment Check

Before first execution, verify Python is available:

```bash
python3 --version  # must be 3.9+
```

If `python3` is not found, try `python --version` or `py -3 --version`. If Python is unavailable or below 3.9, skip to **Path 2 (curl)** in [execution-guide.md](references/execution-guide.md).

#### Default: Run Script

**Script path**: Scripts are in the `scripts/` subdirectory **of this skill's directory** (the directory containing this SKILL.md). **You MUST first locate this skill's installation directory, then ALWAYS use the full absolute path to execute scripts.** Do NOT assume scripts are in the current working directory. Do NOT use `cd` to switch directories before execution.

**Execution note:** Run all scripts in the **foreground** — wait for stdout; do not background.

**Discovery:** Run `python3 <this-skill-dir>/scripts/tts.py --help` first to see all available arguments.

```bash
python3 <this-skill-dir>/scripts/tts.py \
  --request '{"text":"Hello, this is a test.","voice":"Cherry"}' \
  --output output/qwencloud-audio-tts/ \
  --print-response
```

| Argument | Description |
|----------|-------------|
| `--request '{...}'` | JSON request body |
| `--file path.json` | Load request from file |
| `--output dir/` | Save audio and response JSON to directory |
| `--print-response` | Print response to stdout |
| `--model ID` | Override model |
| `--voice NAME` | Override voice |

#### Verify Result

- Exit code `0` + output contains valid JSON with `output.audio` field → **success**
- Non-zero exit, HTTP error, empty response, or error JSON → **fail**
- **Post-execution check**: Verify the output audio file exists and has non-zero size (`ls -la <output_dir>`)
- **MANDATORY — stderr signal check**: After confirming the result, scan the command's stderr output for `[ACTION_REQUIRED]` or `[UPDATE_AVAILABLE]`. If either signal is present, you **MUST** follow the instructions in [Update Check](#update-check-mandatory-post-execution) below before responding to the user.

#### On Failure

If the script fails, match the error output against the diagnostic table below to determine the resolution. If no match, read [execution-guide.md](references/execution-guide.md) for alternative paths: curl commands (Path 2 — standard, instruct, streaming), code generation (Path 3), and autonomous resolution (Path 5).

**If Python is not available at all** → skip directly to Path 2 (curl) in [execution-guide.md](references/execution-guide.md).

---

### CosyVoice — `tts_cosyvoice.py`

CosyVoice requires `dashscope` SDK. Quick start:

```bash
pip install dashscope>=1.24.6
python3 <this-skill-dir>/scripts/tts_cosyvoice.py --text "Hello"
```

> **Full guide**: [cosyvoice-guide.md](references/cosyvoice-guide.md) (setup, voices, examples, errors)

| Error Pattern | Diagnosis | Resolution |
|---------------|-----------|------------|
| `command not found: python3` | Python not on PATH | Try `python` or `py -3`; install Python 3.9+ if missing |
| `Python 3.9+ required` | Script version check failed | Upgrade Python to 3.9+ |
| `SyntaxError` near type hints | Python < 3.9 | Upgrade Python to 3.9+ |
| `QWEN_API_KEY/DASHSCOPE_API_KEY not found` | Missing API key | Obtain key from [QwenCloud Console](https://home.qwencloud.com/api-keys); add to `.env`: `echo 'DASHSCOPE_API_KEY=sk-...' >> .env`; or run **qwencloud-ops-auth** if available |
| `HTTP 401` | Invalid or mismatched key | Run **qwencloud-ops-auth** (non-plaintext check only); verify key is valid |
| `SSL: CERTIFICATE_VERIFY_FAILED` | SSL cert issue (proxy/corporate) | macOS: run `Install Certificates.command`; else set `SSL_CERT_FILE` env var |
| `URLError` / `ConnectionError` | Network unreachable | Check internet; set `HTTPS_PROXY` if behind proxy |
| `HTTP 429` | Rate limited | Wait and retry with backoff |
| `HTTP 5xx` | Server error | Retry with backoff |
| `PermissionError` | Can't write output | Use `--output` to specify writable directory |

## Quick Reference

### Request Fields

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | **Required** — text to synthesize (max 600 chars) |
| `voice` | string | **Required** — voice ID (e.g. `Cherry`, `Ethan`) |
| `model` | string | Model ID (default: `qwen3-tts-flash`) |
| `language_type` | string | `Auto`, `Chinese`, `English`, `Japanese`, `Korean`, `French`, `German`, etc. |
| `instructions` | string | Tone/style instructions (instruct model only) |
| `stream` | bool | Enable streaming (Base64 chunks) |

### Response Fields

| Field | Description |
|-------|-------------|
| `audio_url` | URL of generated audio (valid 24h) |
| `audio_format` | Format (e.g. wav) |
| `sample_rate` | Sample rate (e.g. 24000) |
| `usage` | Character usage |

## Important Notes

- **text**: Max 600 characters per request.
- **instructions**: Only works with `qwen3-tts-instruct-flash`.
- **language_type**: `Auto` for mixed language; specify for better pronunciation.
- **audio_url**: Valid for 24 hours — download promptly.
- **Real-time/streaming TTS**: For WebSocket-based real-time TTS (CosyVoice, qwen3-tts-flash-realtime), a WebSocket client is required. This skill covers the HTTP-based non-real-time API. For real-time streaming use cases, refer to the official docs in [sources.md](references/sources.md).

## Cross-Skill Chaining

When passing generated audio to another skill (e.g., video-gen audio overlay):
- **Pass `audio_url` directly** — scripts detect URL prefixes and pass through without re-upload
- Use `audio_file` only for local playback or non-API operations

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `401 Unauthorized` | Invalid or missing API key | Run **qwencloud-ops-auth** if available; else prompt user to set key (non-plaintext check only) |
| `400` | Invalid parameters (missing text/voice) | Validate request body |
| `429` / `5xx` | Rate limit or server error | Retry with backoff |

## Output Location

Prefer the **current working directory**. Default subdirectory: `./output/qwencloud-audio-tts/`.

**Write prohibition**: NEVER write output files into this skill's installation directory or any `skills/` hierarchy. All generated content must go to `output/` under the current working directory or a user-specified path.

## Update Check (MANDATORY Post-Execution)

After script execution, check stderr for action signals. The script automatically detects update status and emits structured signals. You MUST act on them. This section also applies when the user explicitly asks to check for updates.

### Signal: `[ACTION_REQUIRED] qwencloud-update-check skill is not installed`

When stderr contains this signal, you MUST present the following options to the user and **wait for their response before proceeding**. Do NOT silently skip this.

> The update-check skill is not installed. It keeps you informed about new qwencloud/qwencloud-ai features and bug fixes.
>
> 1) **Install now** — I'll run the install command for you
> 2) **Skip for now** — do nothing this time
> 3) **Never remind me** — permanently suppress this prompt

After the user responds:
- User chooses **1** → run: `npx skills add QwenCloud/qwencloud-ai --skill qwencloud-update-check -y`, then run: `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`
- User chooses **2** → run: `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`, then continue normally
- User chooses **3** → run: `python3 <this-skill-scripts-dir>/gossamer.py --never-install`, then continue normally

### Signal: `[UPDATE_AVAILABLE]`

When stderr contains this signal, you MUST append a brief update notice to your response, including the version info and the update command shown in the stderr output.

### No signal in stderr

If stderr contains neither `[ACTION_REQUIRED]` nor `[UPDATE_AVAILABLE]`, no action is needed — the skill is installed and up to date (or cached within 24h).

### Explicit user request

When the user explicitly asks to check for updates (e.g. "check for updates", "check version"):
1. Look for `qwencloud-update-check/SKILL.md` in sibling skill directories.
2. If found — run: `python3 <qwencloud-update-check-dir>/scripts/check_update.py --print-response` and report the result.
3. If not found — present the install options above.

## References

- [execution-guide.md](references/execution-guide.md) — Fallback paths (curl standard/instruct/streaming, code generation, autonomous)
- [api-guide.md](references/api-guide.md) — API supplementary guide
- [sources.md](references/sources.md) — Official documentation URLs
