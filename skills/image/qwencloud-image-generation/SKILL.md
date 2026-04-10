---
name: qwencloud-image-generation
description: "[QwenCloud] Generate and edit images using Wan and Qwen Image models. Supports text-to-image, image editing (style transfer, subject consistency, text rendering), and interleaved text-image output. TRIGGER when: user wants to create illustrations, product images, artistic designs, posters, text-to-image generation, edit/transform existing images, apply style transfer, generate images based on reference photos, interleaved text-image content, mentions Wan/Qwen Image models/AI art creation, or explicitly invokes this skill by name (e.g. use qwencloud-image-generation). DO NOT TRIGGER when: user wants to understand/analyze existing images or OCR (use qwencloud-vision), video generation (use qwencloud-video-generation), text-only tasks."
compatibility: "Requires Python 3.9+ and curl. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

> **Agent setup**: If your agent doesn't auto-load skills (e.g. Claude Code),
> see [agent-compatibility.md](references/agent-compatibility.md) once per session.

# Qwen Image Generation

Generate and edit images using Wan and Qwen Image models. Supports text-to-image, reference-image editing (style
transfer, subject consistency, multi-image composition, text rendering), and interleaved text-image output.
This skill is part of **qwencloud/qwencloud-ai**.

## Skill directory

Use this skill's internal files to execute and learn. Load reference files on demand when the default path fails or you need details.

| Location | Purpose |
|----------|---------|
| `scripts/image.py` | Default execution — sync/async, upload, download |
| `references/execution-guide.md` | Fallback: curl (sync/async), code generation |
| `references/prompt-guide.md` | Prompt formulas, style keywords, negative_prompt, prompt_extend decision |
| `references/api-guide.md` | API supplement |
| `references/sources.md` | Official documentation URLs |
| `references/agent-compatibility.md` | Agent self-check: register skills in project config for agents that don't auto-load |

## Security

**NEVER output any API key or credential in plaintext.** Always use variable references (`$DASHSCOPE_API_KEY` in shell, `os.environ["DASHSCOPE_API_KEY"]` in Python). Any check or detection of credentials must be **non-plaintext**: report only status (e.g. "set" / "not set", "valid" / "invalid"), never the value. Never display contents of `.env` or config files that may contain secrets.

**When the API key is not configured, NEVER ask the user to provide it directly.** Instead, help create a `.env` file with a placeholder (`DASHSCOPE_API_KEY=sk-your-key-here`) and instruct the user to replace it with their actual key from the [QwenCloud Console](https://home.qwencloud.com/api-keys). Only write the actual key value if the user explicitly requests it.

## Key Compatibility

Scripts require a **standard QwenCloud API key** (`sk-...`). Coding Plan keys (`sk-sp-...`) cannot be used — image generation models are not available on Coding Plan, and Coding Plan does not support the native QwenCloud API. The script detects `sk-sp-` keys at startup and prints a warning. If qwencloud-ops-auth is installed, see its `references/codingplan.md` for full details.

## Mode Selection Guide

| User Want | Mode | Model |
|-----------|------|-------|
| Generate image from text only | **t2i** | `wan2.6-t2i` (default), or `wan2.7-image` / `wan2.7-image-pro` |
| Edit image / apply style transfer based on 1–4 reference images | **image-edit** | `wan2.7-image-pro` / `wan2.7-image` / `wan2.6-image` |
| Subject consistency: generate new images maintaining subject from references | **image-edit** | `wan2.7-image-pro` / `wan2.7-image` / `wan2.6-image` |
| Multi-image composition: combine style from one image, background from another | **image-edit** | `wan2.7-image-pro` / `wan2.7-image` / `wan2.6-image` |
| Single-image editing preserving subject consistency | **i2i** | `wan2.5-i2i-preview` |
| Multi-image fusion: place object from one image into another scene | **i2i** | `wan2.5-i2i-preview` |
| Interleaved text-image output (e.g., tutorials, step-by-step guides) | **interleave** | `wan2.6-image` |
| Fast text-to-image drafts | **t2i** | `wan2.2-t2i-flash` |
| Edit text within images, precise element manipulation | **image-edit** | `qwen-image-2.0-pro` |
| Multi-image fusion with realistic textures | **image-edit** | `qwen-image-2.0-pro` |
| Posters / complex Chinese+English text rendering | **t2i** | `qwen-image-2.0-pro` |
| Text-to-image with fixed aspect ratios (batch) | **t2i** | `qwen-image-plus` / `qwen-image-max` |

## Model Selection

### Wan Series (default)

| Model | Use Case |
|-------|----------|
| **wan2.6-t2i** | **Recommended for text-to-image** — sync + async, best quality |
| **wan2.7-image-pro** | **Multi-function** (4K support) — text-to-image, image editing (0–9 images), sequential multi-image, interactive editing (bbox), thinking mode, color palette. Max 4K for t2i, 2K for editing |
| **wan2.7-image** | **Multi-function** (faster) — same as pro but max 2K, no 4K support |
| **wan2.6-image** | **Image editing** (NOT for pure text-to-image) — requires `reference_images` or `enable_interleave: true`. Style transfer, subject consistency (1–4 images), interleaved text-image output, 2K |
| **wan2.5-i2i-preview** | **Image editing** — single-image editing with subject consistency, multi-image fusion (up to 3 images), async-only |
| **wan2.5-t2i-preview** | Preview — free size within constraints |
| **wan2.2-t2i-flash** | Fast — lower latency |
| **wan2.2-t2i-plus** | Professional — improved stability |

### Qwen Image Series

| Model | Use Case |
|-------|----------|
| **qwen-image-2.0-pro** | Fused generation + editing — text rendering, realistic textures, multi-image (1–3 input, 1–6 output) |
| **qwen-image-2.0** | Accelerated generation + editing |
| **qwen-image-edit-max** | Image editing — 1–6 output images |
| **qwen-image-edit-plus** | Image editing — 1–6 output images |
| **qwen-image-edit** | Image editing — 1 output image only |
| **qwen-image-plus** | Text-to-image — fixed resolutions only (async) |
| **qwen-image-max** | Text-to-image — fixed resolutions only |

Qwen Image editing models (`qwen-image-2.0-pro`, `qwen-image-2.0`, `qwen-image-edit-max/plus/edit`) use the same sync endpoint as `wan2.6-image` (`/multimodal-generation/generation`) with `messages` format. They support text editing in images, element add/delete/replace, style transfer, and multi-image fusion (1–3 input images). Size range: 512x512 to 2048x2048. `qwen-image-2.0-pro` and `qwen-image-2.0` also support pure text-to-image (no reference images needed).

Qwen Image text-to-image models (`qwen-image-plus`, `qwen-image-max`) use a different endpoint (`/text2image/image-synthesis`) with `input.prompt` format (async-only). They support only 5 fixed resolutions: 1664\*928, 1472\*1104, 1328\*1328, 1104\*1472, 928\*1664.

**Choosing between `wan2.6-image` and `wan2.5-i2i-preview` for image editing:**
- `wan2.6-image` supports up to 4 images, higher resolution (2K), interleaved text-image output, and sync mode. Use for multi-image style composition, interleaved tutorials.
- `wan2.5-i2i-preview` uses a simpler prompt-only editing interface (no messages format), supports up to 3 images, async-only. Use for straightforward single-image edits and multi-image object fusion.

1. **User specified a model** → use directly.
2. **Consult the qwencloud-model-selector skill** when model choice depends on requirement, scenario, or pricing.
3. **Text-to-image (prompt only, no reference images)** → use `wan2.6-t2i` (default) or `wan2.7-image` / `wan2.7-image-pro` (multi-function, higher quality). **NEVER use `wan2.6-image` for pure text-to-image** — it will error without reference images or `enable_interleave: true`.
4. **Reference images / image editing / interleaved output** → `wan2.7-image-pro` (recommended), `wan2.7-image`, or `wan2.6-image`.

> **⚠️ Important**: The model list above is a **point-in-time snapshot** and may be outdated. Model availability
> changes frequently. **Always check the [official model list](https://www.qwencloud.com/models)
> for the authoritative, up-to-date catalog before making model decisions.**

> **Model details**: For more information about a specific model, direct the user to its detail page: `https://www.qwencloud.com/models/<model-name>` (replace `<model-name>` with the exact model ID, e.g. `wan2.7-image-pro` → https://www.qwencloud.com/models/wan2.7-image-pro). NEVER modify or guess the model name in the URL.

## Execution

> **⚠️ Multiple artifacts**: When generating multiple files in a single session, you MUST append a numeric suffix to each filename (e.g. `out_1.png`, `out_2.png`) to prevent overwrites.

### Prerequisites

- **API Key**: Check that `DASHSCOPE_API_KEY` (or `QWEN_API_KEY`) is set using a **non-plaintext** check only (e.g. in shell: `[ -n "$DASHSCOPE_API_KEY" ]`; report only "set" or "not set", never the key value). If not set: run the **qwencloud-ops-auth** skill if available; otherwise guide the user to obtain a key from [QwenCloud Console](https://home.qwencloud.com/api-keys) and set it via `.env` file (`echo 'DASHSCOPE_API_KEY=sk-your-key-here' >> .env` in project root or current directory) or environment variable. The script searches for `.env` in the current working directory and the project root. Skills may be installed independently — do not assume qwencloud-ops-auth is present.
- Python 3.9+ (stdlib only, **no pip install needed**)

### Environment Check

Before first execution, verify Python is available:

```bash
python3 --version  # must be 3.9+
```

If `python3` is not found, try `python --version` or `py -3 --version`. If Python is unavailable or below 3.9, skip to **Path 2 (curl)** in [execution-guide.md](references/execution-guide.md).

### Default: Run Script

**Script path**: Scripts are in the `scripts/` subdirectory **of this skill's directory** (the directory containing this
SKILL.md). **You MUST first locate this skill's installation directory, then ALWAYS use the full absolute path to execute
scripts.** Do NOT assume scripts are in the current working directory. Do NOT use `cd` to switch directories before
execution.

**Execution note:** Run all scripts in the **foreground** — wait for stdout; do not background.

**Discovery:** Run `python3 <this-skill-dir>/scripts/image.py --help` first to see all available arguments.

```bash
# Text-to-image (wan2.6-t2i, default)
python3 <this-skill-dir>/scripts/image.py \
  --request '{"prompt":"A cozy flower shop with wooden door"}' \
  --output output/qwencloud-image-generation/images/out.png \
  --print-response

# Image editing with reference images (wan2.6-image)
python3 <this-skill-dir>/scripts/image.py \
  --model wan2.6-image \
  --request '{"prompt":"Apply watercolor painting style to this photo","reference_images":["https://img.alicdn.com/imgextra/i1/NotRealJustExample/photo.jpg"],"n":1,"size":"1K"}' \
  --output output/qwencloud-image-generation/images/out.png \
  --print-response
```

**More examples** (interleaved output, wan2.5-i2i, qwen-image-2.0-pro, qwen-image-plus): See [execution-guide.md](references/execution-guide.md)

| Argument | Description |
|----------|-------------|
| `--request '{...}'` | JSON request body |
| `--file path.json` | Load request from file |
| `--async` | Force async mode (required for wan2.5 and older; auto-enabled for qwen-image-plus/max and interleaved output) |
| `--model ID` | Override model (`wan2.6-t2i` default; see model list in help) |
| `--output path` | Save image to path (or directory for multi-image output) |
| `--print-response` | Print response JSON to stdout |

### Verify Result

- Exit code `0` + output contains valid JSON with `output.results` or `output.task_id` → **success**
- Non-zero exit, HTTP error, empty response, or error JSON → **fail**
- Async: submission must return `output.task_id`; poll must reach `task_status: SUCCEEDED`
- **Post-execution check**: Verify the output file exists and has non-zero size (`ls -la <output_path>`)
- **MANDATORY — stderr signal check**: After confirming the result, scan the command's stderr output for `[ACTION_REQUIRED]` or `[UPDATE_AVAILABLE]`. If either signal is present, you **MUST** follow the instructions in [Update Check](#update-check-mandatory-post-execution) below before responding to the user.

### On Failure

If the script fails, match the error output against the diagnostic table below to determine the resolution. If no match, read [execution-guide.md](references/execution-guide.md) for alternative paths: curl commands (Path 2 — sync and async), code generation (Path 3), and autonomous resolution (Path 5).

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
| `PermissionError` | Can't write output | Use `--output` to specify writable directory |

## Quick Reference

### Request Fields (Common)

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | Text description of the image to generate (required) |
| `negative_prompt` | string | Content to avoid in the image (max 500 chars) |
| `size` | string | Resolution — `1280*1280` (t2i default), `1K`/`2K` or `width*height` (wan2.6-image) |
| `seed` | int | Random seed for reproducibility [0, 2147483647] |
| `model` | string | `wan2.6-t2i` (default) or other Wan model |
| `prompt_extend` | bool | Enable prompt rewriting (default: true; image editing mode only) |

### Request Fields (wan2.7-image-pro / wan2.7-image — Multi-function)

| Field | Type | Description |
|-------|------|-------------|
| `reference_images` | string[] | 0–9 image URLs or local paths |
| `reference_image` | string | Single image URL/path (shorthand) |
| `size` | string | `1K`, `2K` (default), or `4K` (pro only, t2i mode). Or pixel dimensions |
| `enable_sequential` | bool | `true`: sequential multi-image mode (n=1–12). `false` (default): single/batch mode (n=1–4) |
| `n` | int | Images to generate. Sequential mode: 1–12 (default 12). Non-sequential: 1–4 (default 4). **Billed per image.** |
| `thinking_mode` | bool | Enable enhanced reasoning for better quality (default: true). Only for t2i (no images, non-sequential) |
| `bbox_list` | List[List[List[int]]] | Interactive editing regions. Format: `[[[x1,y1,x2,y2],...], ...]`. List length = image count. Empty `[]` for images without edits |
| `color_palette` | array | Custom color theme (3–10 colors). Each: `{"hex":"#C2D1E6","ratio":"23.51%"}`. Sum of ratios = 100%. Non-sequential mode only |
| `watermark` | bool | Add "AI Generated" watermark (default: false) |

**Note**: `thinking_mode` increases latency but improves quality. `enable_sequential` generates a coherent image sequence (e.g., same character across scenes).

### Request Fields (wan2.6-image — Image Editing)

| Field | Type | Description |
|-------|------|-------------|
| `reference_images` | string[] | 1–4 image URLs or local paths for editing mode; 0–1 for interleave mode |
| `reference_image` | string | Single image URL/path (shorthand; `reference_images` takes precedence) |
| `enable_interleave` | bool | `false` (default): image editing mode; `true`: interleaved text-image output |
| `n` | int | Number of images to generate in editing mode (1–4, default: 1). **Billed per image.** |
| `max_images` | int | Max images in interleave mode (1–5, default: 5). **Billed per image.** |
| `watermark` | bool | Add "AI Generated" watermark (default: false) |

### Other Models (wan2.5-i2i, qwen-image-edit, qwen-image-plus/max)

These models have specific parameter requirements:

| Model | Key Differences |
|-------|----------------|
| `wan2.5-i2i-preview` | async-only, 1–3 images, `prompt+images[]` format (not messages) |
| `qwen-image-edit-*` | 1–3 images, n=1–6 (except `qwen-image-edit`: n=1 only), no interleave |
| `qwen-image-plus/max` | async-only, **n fixed at 1**, 5 fixed resolutions only |

**Full parameter tables**: See [api-guide.md](references/api-guide.md#wan25-i2i-preview--general-image-editing) for detailed parameters.

### Size Reference (wan2.6-image)

- **Editing mode**: `1K` (default, ~1280×1280) or `2K` (~2048×2048)
- **Interleave mode**: pixel dimensions with total pixels in [768×768, 1280×1280]

**Common aspect ratios**: `1280*1280` (1:1), `960*1280` (3:4), `1280*960` (4:3), `720*1280` (9:16), `1280*720` (16:9)

### Response Fields

| Field | Description |
|-------|-------------|
| `image_url` | URL of generated image (24h validity). **Use this when chaining to another skill.** |
| `image_urls` | Array of all image URLs (multi-image output, wan2.6-image, qwen-image-edit) |
| `image_count` | Number of generated images |
| `local_path` | Local file path of the downloaded image. **Use this for user preview or non-API operations.** |
| `local_paths` | Array of local file paths (multi-image output) |
| `interleaved_content` | Array of `{type, text/image}` objects (interleave mode) |
| `width` / `height` | Image dimensions |
| `seed` | Seed used |

## API Details

- **Sync endpoint (wan2.6-t2i, wan2.6-image editing, qwen-image-edit series)**: `POST /api/v1/services/aigc/multimodal-generation/generation`
- **Async endpoint (wan2.6 and older t2i)**: `POST /api/v1/services/aigc/image-generation/generation` with `X-DashScope-Async: enable`
- **Async endpoint (wan2.5-i2i-preview)**: `POST /api/v1/services/aigc/image2image/image-synthesis` with `X-DashScope-Async: enable`
- **Async endpoint (qwen-image-plus, qwen-image-max)**: `POST /api/v1/services/aigc/text2image/image-synthesis` with `X-DashScope-Async: enable`
- **wan2.6-t2i resolution**: Total pixels in [1280x1280, 1440x1440], aspect ratio [1:4, 4:1]
- **wan2.6-image resolution**: Editing mode [768x768, 2048x2048]; Interleave mode [768x768, 1280x1280]; aspect ratio [1:4, 4:1]
- **Input images** (wan2.6-image): JPEG/JPG/PNG/BMP/WEBP, 240–8000px per dimension, ≤10MB
- **Local files**: Script auto-uploads to DashScope temp storage (`oss://` URL, 48h TTL). Pass local paths directly — no manual upload step needed.
- **Production**: Default temp storage has **48h TTL** and **100 QPS upload limit** — not suitable for production, high-concurrency, or load-testing. To use your own OSS bucket, set `QWEN_TMP_OSS_BUCKET` and `QWEN_TMP_OSS_REGION` in `.env`, install `pip install alibabacloud-oss-v2`, and provide credentials via `QWEN_TMP_OSS_AK_ID` / `QWEN_TMP_OSS_AK_SECRET` or the standard `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`. Use a RAM user with least-privilege (`oss:PutObject` + `oss:GetObject` on target bucket only). If qwencloud-ops-auth is installed, see its `references/custom-oss.md` for the full setup guide.
- **Interleaved sync**: Requires streaming (`X-DashScope-Sse: enable` + `stream: true`); use async mode via this script instead

## Cross-Skill Chaining

When using generated images as input for another skill (e.g., video-gen i2v, vision analyze):
- **Pass `image_url` directly** — do NOT download and re-pass as local path
- All downstream scripts detect URL prefixes (`https://`, `oss://`) and pass them through without re-upload
- Use `local_path` only for user preview or non-API operations (e.g., opening in editor)

| Scenario | Use |
|----------|-----|
| Feed to another skill (video-gen, vision, image-edit) | `image_url` (URL) |
| Show to user / open in editor | `local_path` (local file) |

## Error Handling

| HTTP | Meaning | Action |
|------|---------|--------|
| 401 | Invalid or missing API key | Run **qwencloud-ops-auth** if available; else prompt user to set key (non-plaintext check only) |
| 400 | Bad request (invalid prompt, size) | Verify parameters and constraints |
| 429 | Rate limited | Retry with exponential backoff |
| 5xx | Server error | Retry with exponential backoff |

> **Usage & billing**: To check actual usage or spending, direct the user to the QwenCloud console:
> [Usage Analytics](https://home.qwencloud.com/analytics) |
> [Pay-as-you-go Billing](https://home.qwencloud.com/billing/pay-as-you-go) |
> [Coding Plan Billing](https://home.qwencloud.com/billing/coding-plan)
>
> **NEVER fabricate, guess, or construct usage/billing/console URLs.** Only provide the exact links listed in this skill. If a URL is not listed here, do not invent one.

## Output Location

Prefer the **current working directory**. Default subdirectory: `./output/qwencloud-image-generation/`.

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

- [execution-guide.md](references/execution-guide.md) — Fallback paths (curl sync/async, code generation, autonomous)
- [api-guide.md](references/api-guide.md) — API supplementary guide
- [sources.md](references/sources.md) — Official documentation URLs
