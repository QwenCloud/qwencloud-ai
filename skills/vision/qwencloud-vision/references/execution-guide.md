# Qwen Vision — Execution Guide

Fallback paths when bundled scripts (Path 1) fail or are unavailable.

## Path 0 · Environment Fix

When scripts fail due to environment issues (not API errors):

1. **`python3` not found**: Try `python --version` or `py -3 --version`. Use whichever returns 3.9+. If none work, help the user install Python 3.9+ from https://www.python.org/downloads/.
2. **Version too low** (`Python 3.9+ required` or `SyntaxError`): Install Python 3.9+ alongside existing Python, then use `python3.9` or `python3.11` explicitly.
3. **SSL errors** (`CERTIFICATE_VERIFY_FAILED`): On macOS, run `/Applications/Python\ 3.x/Install\ Certificates.command`. On Linux/Windows, set `SSL_CERT_FILE` to point to your CA bundle.
4. **Proxy**: Set `HTTPS_PROXY=http://proxy:port` before running the script.

After fixing, retry the scripts (Path 1). If the environment is unfixable, fall through to **Path 2 (curl)** below — curl is available on most systems without Python.

## Path 2 · Direct API Call (curl)

All vision calls use the OpenAI-compatible chat completions endpoint. Images and videos are passed as content entries in the `messages` array.

**Single image (URL):**

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg", "detail": "auto"}},
        {"type": "text", "text": "Describe this image in detail."}
      ]
    }],
    "max_tokens": 512,
    "temperature": 0.2
  }'
```

**Response**: Extract `choices[0].message.content` for the answer text.

For other input types (local base64, multi-image, video, OCR), see [curl-examples.md](curl-examples.md). The pattern is the same — add `image_url`, `video_url`, or change model to `qwen-vl-ocr`.

**Region endpoints** (replace base URL as needed):

| Region | Base URL |
|--------|----------|
| Singapore (default) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |

## Paths 3–5 · Fallback Cascade

When agent-executed paths (1–2) fail or shell is restricted:

**Path 3 — Generate Python script**: Read the relevant script (`scripts/analyze.py`, `scripts/reason.py`, `scripts/ocr.py`, or `scripts/vision_lib.py`) to understand the API logic (base64 encoding, streaming, structured output). Write a self-contained Python script (stdlib `urllib`) tailored to the user's task. Present it for the user to save and run. Use `os.environ["DASHSCOPE_API_KEY"]` — never hardcode or expose the key.

**Path 4 — Generate curl commands**: Customize the curl templates from Path 2 with the user's specific parameters (model, image URLs, prompt). Present as ready-to-copy commands.

**Path 5 — Autonomous resolution**: Read `scripts/*.py` source and `references/*.md` to understand the full API contract. Reason about alternative approaches and implement.
