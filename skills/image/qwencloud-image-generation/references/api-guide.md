# Qwen Image Generation — API Supplementary Guide

> **Content validity**: 2026-03 | **Sources**: [Text-to-Image API](https://docs.qwencloud.com/developer-guides/image-generation/text-to-image) · [Image Generation Guide](https://docs.qwencloud.com/developer-guides/image-generation/text-to-image) · [Wan2.6-Image API](https://docs.qwencloud.com/api-reference/image-generation/wan26-image-gen-edit/create-task)

---

## Definition

Generate and edit images using Wan and Qwen-Image models. The Wan series excels at realistic photography and diverse artistic styles. The Qwen-Image series excels at rendering complex Chinese and English text (posters, layouts). **wan2.6-t2i supports synchronous HTTP calls** for text-to-image. **wan2.6-image supports image editing, style transfer, subject consistency, and interleaved text-image output.** Older models use asynchronous invocation (submit task → poll result).

---

## Use Cases

| Scenario | Recommended Model | Notes |
|----------|------------------|-------|
| General creative / realistic photography | `wan2.6-t2i` | Latest t2i model, best quality, supports synchronous calls. |
| Posters / complex text rendering | `qwen-image-2.0-pro` or `wan2.6-t2i` | Strongest Chinese/English text rendering. |
| Fast drafts / batch generation | `wan2.2-t2i-flash` | Lowest latency. |
| Custom resolutions | `qwen-image-2.0` or Wan series | Flexible aspect ratios. |
| Image editing / style transfer | `wan2.6-image` | 1–4 input images, text prompt to edit/transform. |
| Text editing in images / element manipulation | `qwen-image-edit-max` or `qwen-image-2.0-pro` | Precise text modification, element add/delete/replace. |
| Subject consistency across images | `wan2.6-image` | Maintain subject identity across generated images. |
| Multi-image composition | `wan2.6-image` | Combine style from one image with background from another. |
| Multi-image fusion with text rendering | `qwen-image-2.0-pro` | 1–3 input images, text rendering, realistic textures. |
| Interleaved text-image output | `wan2.6-image` | Generate mixed text+image content (tutorials, guides). |
| Fixed-resolution batch text-to-image | `qwen-image-plus` | 5 fixed resolutions, async API, good for batch workflows. |

---

## Key Usage

### Synchronous Call (wan2.6, recommended)

Returns the result in a single request. Suitable for most scenarios.

```bash
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "wan2.6-t2i",
    "input": {
        "messages": [{"role": "user", "content": [{"text": "A cozy flower shop with wooden door and flowers on display"}]}]
    },
    "parameters": {"size": "1280*1280", "n": 1, "prompt_extend": true}
}'
```

The image URL is at `output.choices[0].message.content[0].image` in the response.

### Asynchronous Call (qwen-image-plus, older Wan models)

```python
from dashscope import ImageSynthesis
import dashscope, os

dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
rsp = ImageSynthesis.call(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-image-plus",
    prompt="A healing-style hand-drawn poster featuring three puppies playing with a ball on green grass",
    n=1, size='1664*928', prompt_extend=True, watermark=False,
)
print(rsp.output.results[0].url)  # Image URL, valid for 24 hours
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `size` | `1280*1280` | Resolution as width*height. Total pixels must be between 1280×1280 and 1440×1440. Aspect ratio must be between 1:4 and 4:1. |
| `n` | 4 | Number of images to generate (1–4). **Billed per image.** Set to 1 for testing. |
| `prompt_extend` | true | LLM rewrites the prompt. Significantly improves results for short prompts but adds 3–4 seconds of latency. |
| `negative_prompt` | — | Content to exclude from the image. Max 500 characters. |
| `watermark` | false | Adds an "AI-generated" watermark in the lower-right corner. |
| `seed` | random | Fixed seed produces more consistent results (not guaranteed identical). Range: [0, 2147483647]. |

### Common Resolutions

| Aspect Ratio | Size |
|-------------|------|
| 1:1 | 1280×1280 |
| 4:3 | 1472×1104 |
| 3:4 | 1104×1472 |
| 16:9 | 1696×960 |
| 9:16 | 960×1696 |

---

## wan2.6-image — Image Editing & Interleaved Output

### Overview

The `wan2.6-image` model operates in two modes controlled by the `enable_interleave` parameter:

- **Image editing mode** (`enable_interleave=false`, default): Takes 1–4 reference images + text prompt. Performs style transfer, subject consistency, composition, and image editing.
- **Interleaved text-image mode** (`enable_interleave=true`): Takes 0–1 reference image + text prompt. Generates mixed text and image content (e.g., tutorials, step-by-step guides).

### Endpoints

Same as other Wan models:
- **Sync**: `POST /api/v1/services/aigc/multimodal-generation/generation` (editing mode only; interleave requires streaming or async)
- **Async**: `POST /api/v1/services/aigc/image-generation/generation` with `X-DashScope-Async: enable`

### Image Editing Mode Examples

**Style transfer** (single reference):
```bash
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "wan2.6-image",
    "input": {
        "messages": [{"role": "user", "content": [
            {"text": "Convert this photo to a watercolor painting style"},
            {"image": "https://example.com/photo.jpg"}
        ]}]
    },
    "parameters": {"size": "1K", "n": 1, "prompt_extend": true, "watermark": false, "enable_interleave": false}
  }'
```

**Multi-image composition** (style from image 1 + background from image 2):
```bash
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "wan2.6-image",
    "input": {
        "messages": [{"role": "user", "content": [
            {"text": "Generate a sunset scene based on the style of image 1 and the background of image 2"},
            {"image": "https://example.com/style_ref.jpg"},
            {"image": "https://example.com/background_ref.jpg"}
        ]}]
    },
    "parameters": {"size": "1K", "n": 1, "prompt_extend": true, "enable_interleave": false}
  }'
```

### Interleaved Text-Image Output Example (async)

```bash
# Step 1: Submit task
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/image-generation/generation' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-DashScope-Async: enable' \
  -d '{
    "model": "wan2.6-image",
    "input": {
        "messages": [{"role": "user", "content": [
            {"text": "Give me a three-image tutorial for making latte art"}
        ]}]
    },
    "parameters": {"enable_interleave": true, "max_images": 3, "size": "1280*1280"}
  }'

# Step 2: Poll with task_id (repeat every 10s)
curl -sS "https://dashscope-intl.aliyuncs.com/api/v1/tasks/TASK_ID" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY"
```

The response contains interleaved `{type: "text", text: "..."}` and `{type: "image", image: "URL"}` content items in `output.choices[0].message.content`.

### Parameters (wan2.6-image)

| Parameter | Default | Editing Mode | Interleave Mode | Description |
|-----------|---------|:---:|:---:|-------------|
| `enable_interleave` | false | false | **true** | Switches between image editing and interleaved output modes |
| `size` | `1K` | `1K`/`2K` or `W*H` (total px [768², 2048²]) | `W*H` (total px [768², 1280²]) | Output resolution |
| `n` | 4 (editing) / 1 (interleave) | 1–4 | Must be 1 | Number of output images. **Billed per image.** |
| `max_images` | 5 | — | 1–5 | Max images in interleaved output. **Billed per image.** |
| `prompt_extend` | true | Yes | — | Intelligent prompt rewriting (editing mode only) |
| `negative_prompt` | — | Yes | Yes | Content to exclude |
| `watermark` | false | Yes | Yes | "AI Generated" watermark |
| `seed` | random | Yes | Yes | Reproducibility seed [0, 2147483647] |

### Input Image Constraints

- Formats: JPEG, JPG, PNG (no alpha), BMP, WEBP
- Resolution: 240–8000px per dimension
- Max file size: 10MB per image
- Editing mode: **1–4** images required
- Interleave mode: **0–1** image (optional)

### Size Reference for wan2.6-image

In **editing mode** (`enable_interleave=false`): use `1K` (default, ~1280×1280) or `2K` (~2048×2048), or specify pixel dimensions with total pixels in [768×768, 2048×2048].

In **interleave mode** (`enable_interleave=true`): use pixel dimensions with total pixels in [768×768, 1280×1280].

| Aspect Ratio | Size |
|-------------|------|
| 1:1 | 1280*1280 |
| 2:3 | 800*1200 |
| 3:2 | 1200*800 |
| 3:4 | 960*1280 |
| 4:3 | 1280*960 |
| 9:16 | 720*1280 |
| 16:9 | 1280*720 |

---

## wan2.5-i2i-preview — General Image Editing

### Overview

The `wan2.5-i2i-preview` model provides image-to-image editing via a simpler prompt+images API. It preserves subject consistency during edits and supports multi-image fusion with up to 3 reference images.

**Key differences from `wan2.6-image`:**

- Uses `input.prompt` + `input.images[]` format (not messages)
- **Async-only** (no sync support)
- Dedicated endpoint: `/api/v1/services/aigc/image2image/image-synthesis`
- Max 3 images (vs wan2.6-image's 4)
- Max output resolution: 1280*1280 total pixels (vs wan2.6-image's 2048*2048)
- Response uses `output.results[].url` format (vs choices format)
- Singapore (`ap-southeast-1`) only

### Endpoint

**Async only:**

- Singapore: `POST https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis`

### Single-Image Editing Example

```bash
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-DashScope-Async: enable' \
  -d '{
    "model": "wan2.5-i2i-preview",
    "input": {
        "prompt": "Change the floral dress to a vintage-style lace long dress",
        "images": ["https://example.com/photo.jpg"]
    },
    "parameters": {"prompt_extend": true, "n": 1}
  }'
```

### Multi-Image Fusion Example

```bash
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-DashScope-Async: enable' \
  -d '{
    "model": "wan2.5-i2i-preview",
    "input": {
        "prompt": "Place the alarm clock from Image 1 next to the vase on the dining table in Image 2",
        "images": [
            "https://example.com/clock.jpg",
            "https://example.com/table.jpg"
        ]
    },
    "parameters": {"prompt_extend": true, "n": 1}
  }'
```

Then poll with `GET /api/v1/tasks/{task_id}`. Response contains `output.results[].url`.

### Parameters (wan2.5-i2i-preview)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt` | — | **Required.** Text instruction for the edit. |
| `images` | — | **Required.** Array of 1–3 image URLs. Array order = image numbering in prompt. |
| `negative_prompt` | — | Content to exclude. Max 500 chars. |
| `size` | auto (1280*1280 px) | Output resolution. Total pixels [768*768, 1280*1280], aspect ratio [1:4, 4:1]. |
| `n` | 4 | Number of images (1–4). **Billed per image.** Set to 1 for testing. |
| `prompt_extend` | true | Smart prompt rewriting. |
| `watermark` | false | "AI Generated" watermark. |
| `seed` | random | Reproducibility. If n>1, images use seed, seed+1, seed+2, etc. |

### Input Image Constraints

- Formats: JPEG, JPG, PNG (alpha ignored), BMP, WEBP
- Resolution: 384–5000px per dimension
- Max file size: 10MB per image
- Max 3 images per request

---

## Qwen Image Series

### Overview

The Qwen Image series consists of two sub-families with **different API endpoints**:

- **Editing models** (`qwen-image-2.0-pro`, `qwen-image-2.0`, `qwen-image-edit-max/plus/edit`): Use the same `multimodal-generation/generation` endpoint as `wan2.6-image`. Support image editing with 1–3 reference images, and `qwen-image-2.0-pro/2.0` also support pure text-to-image.
- **Text-to-image models** (`qwen-image-plus`, `qwen-image-max`): Use the `text2image/image-synthesis` endpoint (async-only). Fixed resolutions, `input.prompt` format.

### Editing Models — Endpoint & Parameters

**Endpoint**: Same as wan2.6-image — `POST /api/v1/services/aigc/multimodal-generation/generation`

**Payload format**: `messages` with `image` + `text` content items (same as wan2.6-image).

```bash
curl -sS 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen-image-2.0-pro",
    "input": {
        "messages": [{"role": "user", "content": [
            {"image": "https://example.com/girl.jpg"},
            {"image": "https://example.com/dress.jpg"},
            {"text": "Make the girl from Image 1 wear the black dress from Image 2"}
        ]}]
    },
    "parameters": {"n": 2, "size": "1024*1536", "prompt_extend": true, "watermark": false}
  }'
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n` | 1 | Output images: 1–6 (`qwen-image-edit`: 1 only). **Billed per image.** |
| `size` | `1024*1024` | width\*height. Total pixels 512×512–2048×2048. |
| `prompt_extend` | true | Intelligent prompt rewriting. |
| `watermark` | false | "AI Generated" watermark. |
| `negative_prompt` | — | Content to exclude. |
| `seed` | random | Reproducibility seed [0, 2147483647]. |

**Input image constraints**: JPG, JPEG, PNG, BMP, TIFF, WEBP, GIF. 384–3072px per dimension. ≤10MB per image. Max 3 images.

**Key differences from `wan2.6-image`**:
- Max 3 input images (vs wan2.6-image's 4)
- `n` supports up to 6 (vs wan2.6-image's 4)
- Does **NOT** support `enable_interleave`
- `qwen-image-2.0-pro` and `qwen-image-2.0` can also do pure text-to-image (text-only message, no reference images)

### Text-to-Image Models — Endpoint & Parameters

**Endpoint**: `POST /api/v1/services/aigc/text2image/image-synthesis` (async-only)

**Payload format**: `input.prompt` (NOT messages format).

```bash
curl -sS -X POST 'https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-DashScope-Async: enable' \
  -d '{
    "model": "qwen-image-plus",
    "input": {
        "prompt": "A healing-style poster featuring three puppies playing on green grass"
    },
    "parameters": {"size": "1664*928", "n": 1, "prompt_extend": true, "watermark": false}
  }'
```

Then poll with `GET /api/v1/tasks/{task_id}`. Response contains `output.results[].url`.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n` | 1 | Output images (1–4). **Billed per image.** |
| `size` | `1328*1328` | Fixed resolutions only (see below). |
| `prompt_extend` | true | Intelligent prompt rewriting. |
| `watermark` | false | "AI Generated" watermark. |
| `negative_prompt` | — | Content to exclude. |
| `seed` | random | Reproducibility seed. |

**Fixed resolutions for qwen-image-plus/max:**

| Aspect Ratio | Size |
|-------------|------|
| 16:9 | 1664×928 |
| 4:3 | 1472×1104 |
| 1:1 | 1328×1328 |
| 3:4 | 1104×1472 |
| 9:16 | 928×1664 |

---

## Important Notes

1. **Image URLs are valid for only 24 hours.** Download and save images immediately after generation.
2. **Cost = unit price × number of images.** The `n` and `max_images` parameters directly affect cost. Always set `n=1` during testing.
3. **prompt_extend trade-off.** Significantly improves short prompts, but adds 3–4s latency and may drift from original intent. Set `prompt_extend=false` when you need precise control over composition.
4. **Synchronous vs. asynchronous.** wan2.6-t2i, wan2.6-image (editing mode), and qwen-image-edit series support synchronous calls. Interleaved text-image sync requires streaming; use async mode. wan2.5 and earlier models use async only. `qwen-image-plus` and `qwen-image-max` use async text2image endpoint only.
5. **Prompt length limit.** Supports both Chinese and English. Maximum 2,000 characters for wan2.6-image, 2,100 characters for wan2.6-t2i; excess is automatically truncated.
6. **Region isolation.** API key, endpoint, and model must belong to the same region. Cross-region calls result in authentication failures.
7. **Async task_id is valid for 24 hours.** Do not create duplicate tasks; use polling to retrieve the result.

---

## FAQ

**Q: How do I choose between wan2.6-t2i and qwen-image-2.0-pro?**
A: Use wan2.6-t2i for realistic photography and diverse artistic styles. Use qwen-image-2.0-pro for complex text rendering tasks (posters, PPT illustrations, coupons). Both handle text well, but Qwen-Image is stronger for complex layouts.

**Q: When should I use wan2.6-image vs wan2.6-t2i?**
A: **Always use `wan2.6-t2i` for pure text-to-image (prompt only, no reference images).** `wan2.6-image` is an image editing model — it requires either `reference_images` (1–4 images for style transfer, subject consistency, editing) or `enable_interleave: true` (for interleaved text-image output). Using `wan2.6-image` without either will error or auto-fallback to `wan2.6-t2i`.

**Q: How do I get more consistent results?**
A: Use the `seed` parameter to fix the random seed. Disable `prompt_extend` to prevent the LLM from rewriting and drifting from your intent. Use `negative_prompt` to exclude unwanted elements.

**Q: Does the API support image-to-image / reference images?**
A: Yes, `wan2.6-image` supports image editing with 1–4 reference images, and `qwen-image-edit` series supports 1–3 reference images. Use the `reference_images` field in the script (URLs or local paths; local files are auto-uploaded). For multi-image composition, reference images by order in the prompt: "the style of image 1 and the background of image 2".

**Q: How does interleaved text-image output work?**
A: Set `enable_interleave=true` with `wan2.6-image`. The model generates mixed text and image content. Use async mode (the script auto-enables it). The response contains interleaved text and image items in `output.choices[0].message.content`. The script saves images and a markdown file. Note: `qwen-image-edit` series does **not** support interleaved output.

**Q: How do I optimize costs for batch generation?**
A: Set `n=1` to generate and evaluate one image at a time. Increase `n` after confirming quality. wan2.2-t2i-flash has the lowest per-image price and is suitable for batch testing.

**Q: When to use qwen-image-plus vs qwen-image-2.0-pro for text-to-image?**
A: `qwen-image-plus` uses the `text2image` endpoint with fixed resolutions — good for batch workflows with standard aspect ratios. `qwen-image-2.0-pro` uses the `multimodal-generation` endpoint with flexible resolutions and can also do image editing. Use `qwen-image-plus` for simple text-to-image; use `qwen-image-2.0-pro` when you need text rendering precision or image editing.

**Q: What's the difference between qwen-image-edit series and wan2.6-image?**
A: Both use the `multimodal-generation` endpoint with `messages` format. Key differences: qwen-image-edit supports max 3 input images (vs wan's 4), `n` up to 6 (vs wan's 4), and does not support interleaved output. qwen-image-edit excels at precise text editing in images and element manipulation.
