---
name: qwencloud-video-generation
description: "[QwenCloud] Generate videos using Wan models. Supports text-to-video, image-to-video, first+last frame, reference-based role-play, and video editing (VACE). TRIGGER when: user wants to create, generate, or edit video content, mentions video generation/animation/video clips/Wan models, or explicitly invokes this skill by name (e.g. use qwencloud-video-generation). DO NOT TRIGGER when: user wants to generate images (use qwencloud-image-generation), understand/analyze existing videos (use qwencloud-vision), text-only tasks."
compatibility: "Requires Python 3.9+ and curl. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

> **Agent setup**: If your agent doesn't auto-load skills (e.g. Claude Code),
> see [agent-compatibility.md](references/agent-compatibility.md) once per session.

# Qwen Video Generation

Generate videos using Wan models. All tasks are **asynchronous** — submit, then poll until
completion.
This skill is part of **qwencloud/qwencloud-ai**.

> **⚠️ Critical Parameter Differences by Mode:**
> - **kf2v (First+Last Frame)**: Duration is **fixed at 5 seconds** — other values will fail. Output is **silent only**.
> - **Resolution parameter varies**: t2v/r2v/vace use `size` (e.g. `"1280*720"`); i2v/kf2v use `resolution` (e.g. `"720P"`).

## Skill directory

Use this skill's internal files to execute and learn. Load reference files on demand when the default path fails or you need details.

| Location | Purpose |
|----------|---------|
| `scripts/video.py` | Default execution — mode auto-detect, submit, poll, download |
| `references/execution-guide.md` | Fallback: curl for all 5 modes, code generation |
| `references/request-fields.md` | Field tables and audio handling by mode |
| `references/workflows.md` | Duration extensions, multi-shot, VACE pipelines |
| `references/polling-guide.md` | Polling patterns and timing |
| `references/merge-media.md` | Concat, trim, audio overlay — ffmpeg/moviepy recipes |
| `references/prompt-guide.md` | Per-mode prompt formulas, sound description, multi-shot structure |
| `references/examples.md` | Full script examples per mode |
| `references/sources.md` | Official documentation URLs |
| `references/agent-compatibility.md` | Agent self-check: register skills in project config for agents that don't auto-load |

## Security

**NEVER output any API key or credential in plaintext.** Always use variable references (`$DASHSCOPE_API_KEY` in shell, `os.environ["DASHSCOPE_API_KEY"]` in Python). Any check or detection of credentials must be **non-plaintext**: report only status (e.g. "set" / "not set", "valid" / "invalid"), never the value. Never display contents of `.env` or config files that may contain secrets.

**When the API key is not configured, NEVER ask the user to provide it directly.** Instead, help create a `.env` file with a placeholder (`DASHSCOPE_API_KEY=sk-your-key-here`) and instruct the user to replace it with their actual key from the [QwenCloud Console](https://home.qwencloud.com/api-keys). Only write the actual key value if the user explicitly requests it.

## Key Compatibility

Scripts require a **standard QwenCloud API key** (`sk-...`). Coding Plan keys (`sk-sp-...`) cannot be used — video generation models are not available on Coding Plan, and Coding Plan does not support the native QwenCloud API. Video generation incurs per-second charges on standard keys. The script detects `sk-sp-` keys at startup and prints a warning. If qwencloud-ops-auth is installed, see its `references/codingplan.md` for full details.

## Mode Selection Guide

| User Want | Mode | Key Field |
|-----------|------|-----------|
| Generate video from text description only | **t2v** | `prompt` only |
| Animate a single image | **i2v** | `img_url` or `reference_image` |
| Transition between two images (**⚠️ 5s fixed, silent only**) | **kf2v** | `first_frame_url` + `last_frame_url` |
| Role-play: make characters act a new script | **r2v** | `reference_urls` (up to 5) |
| Video editing: multi-image ref, repainting, local edit, extend, outpaint | **vace** | `function` |

### Model Selection

1. **User specified a model** → use directly.
2. **Consult the qwencloud-model-selector skill** when model choice depends on capability, scenario, or pricing.
3. **No signal, clear task** → per-mode defaults: t2v → `wan2.6-t2v`, i2v → `wan2.6-i2v-flash`, kf2v → `wan2.2-kf2v-flash`, r2v → `wan2.6-r2v-flash`, vace → `wan2.1-vace-plus`.

## Models

### t2v (Text-to-Video)

| Model | Features |
|-------|----------|
| `wan2.6-t2v` **recommended** | Audio, multi-shot, 2–15s, 720P/1080P |
| `wan2.5-t2v-preview` | Audio, 5s/10s, 480P/720P/1080P |
| `wan2.2-t2v-plus` | Silent, 5s, 480P/1080P |

### i2v (Image-to-Video)

| Model | Features |
|-------|----------|
| `wan2.6-i2v-flash` **recommended** | Audio/silent, multi-shot, 2–15s, 720P/1080P |
| `wan2.6-i2v` | Audio, multi-shot, 2–15s, 720P/1080P |
| `wan2.5-i2v-preview` | Audio, 5s/10s, 480P/720P/1080P |

### kf2v / r2v / vace

| Model                                  | Features                                           |
|----------------------------------------|----------------------------------------------------|
| `wan2.2-kf2v-flash` **(kf2v default)** | Silent, 5s, 480P/720P/1080P                        |
| `wan2.6-r2v`                           | Audio, single/multi character, 2–10s, 720P/1080P   |
| `wan2.6-r2v-flash` **(r2v default)**   | Audio/silent, multi-character, 2–10s, 720P/1080P   |
| `wan2.1-vace-plus` **(vace)**         | Multi-image ref, repainting, local edit, ≤5s, 720P |

> **⚠️ Important**: The model list above is a **point-in-time snapshot** and may be outdated. Model availability
> changes frequently. **Always check the [official model list](https://www.qwencloud.com/models)
> for the authoritative, up-to-date catalog before making model decisions.**

## Execution

> **⚠️ Multiple artifacts**: When generating multiple files in a single session, you MUST append a numeric suffix to each filename (e.g. `out_1.mp4`, `out_2.mp4`) to prevent overwrites.

### Prerequisites

- **API Key**: Check that `DASHSCOPE_API_KEY` (or `QWEN_API_KEY`) is set using a **non-plaintext** check only (e.g. in shell:
  `[ -n "$DASHSCOPE_API_KEY" ]`; report only "set" or "not set", never the key value). If not set: run the *
  *qwencloud-ops-auth** skill if available; otherwise guide the user to obtain a key from [QwenCloud Console](https://home.qwencloud.com/api-keys) and set it via `.env` file (
  `echo 'DASHSCOPE_API_KEY=sk-your-key-here' >> .env` in project root or current directory) or environment variable. The
  script searches for `.env` in the current working directory and the project root. Skills may be installed
  independently — do not assume qwencloud-ops-auth is present.
- Python 3.9+ (stdlib only, **no pip install needed**)
- For media merging (concat, trim, audio overlay): see [merge-media.md](references/merge-media.md) for ffmpeg/moviepy recipes suited to the user's environment

### Environment Check

Before first execution, verify Python is available:

```bash
python3 --version  # must be 3.9+
```

If `python3` is not found, try `python --version` or `py -3 --version`. If Python is unavailable or below 3.9, skip to **Path 2 (curl)** in [execution-guide.md](references/execution-guide.md).

### Default: Run Script

**Script path**: Scripts are in the `scripts/` subdirectory **of this skill's directory** (the directory containing this SKILL.md). **You MUST first locate this skill's installation directory, then ALWAYS use the full absolute path to execute scripts.** Do NOT assume scripts are in the current working directory. Do NOT use `cd` to switch directories before execution.

**Execution note:** Run all scripts in the **foreground** — wait for stdout; do not background.

**Discovery:** Run `python3 <this-skill-dir>/scripts/video.py --help` first to see all available arguments.

```bash
python3 <this-skill-dir>/scripts/video.py \
  --request '{"prompt":"A detective in a rainy city at night","size":"1280*720","duration":5}' \
  --print-response
```

| Argument | Description |
|----------|-------------|
| `--request '{...}'` | JSON request body |
| `--file path.json` | Load request from file |
| `--mode MODE` | Override auto-detected mode (t2v/i2v/kf2v/r2v/vace) |
| `--model ID` | Override model |
| `--output dir/` | Save video and response JSON |
| `--print-response` | Print response JSON to stdout |
| `--submit-only` | Submit and exit (print task_id) |
| `--task-id ID` | Operate on existing task |
| `--poll-interval N` | Seconds between polls (default: 15) |
| `--timeout N` | Max wait seconds (default: 600) |

### Verify Result

- Exit code `0` + response has `output.task_id` → **submission success**
- Poll reaches `task_status: SUCCEEDED` → **generation complete**
- Non-zero exit, HTTP error, or `FAILED` status → **fail**
- **Post-execution check**: Verify the output video file exists and has non-zero size (`ls -la <output_dir>`)
- **MANDATORY — stderr signal check**: After confirming the result, scan the command's stderr output for `[ACTION_REQUIRED]` or `[UPDATE_AVAILABLE]`. If either signal is present, you **MUST** follow the instructions in [Update Check](#update-check-mandatory-post-execution) below before responding to the user.

### On Failure

If the script fails, match the error output against the diagnostic table below to determine the resolution. If no match, read [execution-guide.md](references/execution-guide.md) for alternative paths: curl commands (Path 2 — all 5 modes), code generation (Path 3), and autonomous resolution (Path 5).

**If Python is not available at all** → skip directly to Path 2 (curl) in [execution-guide.md](references/execution-guide.md).

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
| `ImportError: moviepy` | moviepy not installed | `pip install moviepy`, or use system ffmpeg instead (see [merge-media.md](references/merge-media.md)) |
| `PermissionError` | Can't write output | Use `--output` to specify writable directory |

## Request Fields Summary

All modes require `prompt`. See [request-fields.md](references/request-fields.md) for full field tables per mode.

### ⚠️ Resolution Parameter by Mode (Critical)

| Mode | Parameter | Format | Example |
|------|-----------|--------|--------|
| t2v | `size` | `"WxH"` | `"1280*720"`, `"1920*1080"` |
| r2v | `size` | `"WxH"` | `"1280*720"`, `"1920*1080"` |
| vace | `size` | `"WxH"` | `"1280*720"` |
| i2v | `resolution` | `"xxxP"` | `"720P"`, `"1080P"` |
| kf2v | `resolution` | `"xxxP"` | `"480P"`, `"720P"`, `"1080P"` |

> **Using the wrong parameter name will cause the API call to fail.**

### Mode-Specific Required Fields

- i2v needs `img_url`/`reference_image`. kf2v needs `first_frame_url` + `last_frame_url`. r2v needs `reference_urls`. vace needs `function`.

## Cost Estimation

> 🚨 **NEVER guess or fabricate any price figure.** Always direct the user to the
> [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing) for exact rates.

Cost is billed per second of generated video. Price varies by model and resolution. For the latest rates, check
the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing).

| Model            | 720P (USD)         | 1080P (USD)        |
|------------------|--------------------|--------------------|
| wan2.6-t2v       | per-second billing | per-second billing |
| wan2.6-i2v-flash | per-second billing | per-second billing |
| wan2.6-r2v-flash | per-second billing | per-second billing |

Quick example: wan2.6-t2v 5s 720P — check
the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing) for current per-second
rates. Some models may offer a limited free quota — verify availability in the
user's [QwenCloud console](https://home.qwencloud.com/free-quota) before assuming any call
is free.

## Local File Handling

When the user provides local file paths (images, videos, audio), pass them directly to the script. The script **automatically uploads** local files to DashScope temporary storage (`oss://` URL, 48h TTL) and injects the `X-DashScope-OssResourceResolve: enable` header. No manual upload step is needed.

> **Production**: Default temp storage has **48h TTL** and **100 QPS upload limit** — not suitable for production, high-concurrency, or load-testing. To use your own OSS bucket, set `QWEN_TMP_OSS_BUCKET` and `QWEN_TMP_OSS_REGION` in `.env`, install `pip install alibabacloud-oss-v2`, and provide credentials via `QWEN_TMP_OSS_AK_ID` / `QWEN_TMP_OSS_AK_SECRET` or the standard `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`. Use a RAM user with least-privilege (`oss:PutObject` + `oss:GetObject` on target bucket only). If qwencloud-ops-auth is installed, see its `references/custom-oss.md` for the full setup guide.

## Cross-Skill Chaining

When using output from another skill as input (e.g., image-gen → i2v, audio-tts → audio overlay):
- **Pass the URL directly** (e.g., `"img_url": "<image_url from image-gen>"`) — do NOT download and re-pass as local path
- The script detects URL prefixes (`https://`, `oss://`) and passes them through without re-upload
- Use `local_path` from the response only for user preview or non-API operations

When passing this skill's output to another skill (e.g., vace edit, vision analyze):
- **Pass `video_url` from the response** — do NOT download and re-pass as local path

| Scenario | Use |
|----------|-----|
| Feed to another skill | `video_url` / `image_url` (URL) |
| Show to user / local playback | `local_path` (local file) |

## Important Notes

- **Async only**: All video APIs require `X-DashScope-Async: enable` header.
- **kf2v**: Uses a **different API endpoint**. Duration **fixed at 5s**, **silent only**.
- **r2v**: Use `character1`/`character2`/... in prompt. Up to 5 references (max 3 videos).
- **vace**: Must specify `function`. **Silent only**, output **≤5s**.
- **Multi-shot**: Set `shot_type: "multi"` AND `prompt_extend: true`.
- **Video URL expires in 24h** — the script auto-downloads to `--output` dir. When chaining to another skill (e.g., vace edit), pass `video_url` directly — do NOT re-download.
- For advanced workflows → see [workflows.md](references/workflows.md).

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `401 Unauthorized` | Invalid or missing API key | Run **qwencloud-ops-auth** if available; else prompt user to set key (non-plaintext check only) |
| `current user api does not support synchronous calls` | Missing async header | Add `X-DashScope-Async: enable` |
| `429` / `5xx` | Rate limit or server error | Retry with backoff |
| Task `FAILED` | Generation failed | Check `output.message` in poll response |

## Output Location

Prefer the **current working directory**. Default subdirectory: `./output/qwencloud-video-generation/`.

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

- [execution-guide.md](references/execution-guide.md) — Fallback paths (curl for all modes, code generation, autonomous)
- [request-fields.md](references/request-fields.md) — Detailed field tables by mode + audio handling
- [workflows.md](references/workflows.md) — Duration extensions, audio workarounds, multi-shot, VACE pipelines
- [polling-guide.md](references/polling-guide.md) — Polling patterns and timing recommendations
- [merge-media.md](references/merge-media.md) — Guide for generating merge/trim/audio-overlay code
- [examples.md](references/examples.md) — Full script execution examples for all modes
- [sources.md](references/sources.md) — Official documentation URLs
