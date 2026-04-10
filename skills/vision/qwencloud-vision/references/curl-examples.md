# Vision curl Examples

Additional curl templates for Path 2 · Direct API Call. The primary example (single image URL) is in SKILL.md. These cover other common input scenarios.

All examples use the OpenAI-compatible chat completions endpoint. Replace the base URL for different regions (see SKILL.md Region endpoints table).

## Local Image (Base64)

Encode the file inline. **Only for small files < 7 MB** (base64 adds ~33%; API limit is 10 MB). For larger files or videos, use Path 1 (Script Execution) with `--upload-files`, or provide a URL instead.

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,'"$(base64 < image.jpg)"'"}},
        {"type": "text", "text": "What is in this image?"}
      ]
    }],
    "max_tokens": 512
  }'
```

## Multi-Image Comparison

Include multiple `image_url` entries in the content array:

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"}},
        {"type": "image_url", "image_url": {"url": "https://img.alicdn.com/imgextra/i2/O1CN01ktT8451iQutqReELT_!!6000000004408-0-tps-689-487.jpg"}},
        {"type": "text", "text": "Compare these two images."}
      ]
    }],
    "max_tokens": 1024
  }'
```

## Video Understanding

For local videos < 7 MB (e.g. short generated clips), base64 works. For larger videos, **use a URL** (online or temp-uploaded via `--upload-files`).

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.6-plus",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "video_url", "video_url": {"url": "https://img.alicdn.com/imgextra/i1/NotRealJustExample/video.mp4"}},
        {"type": "text", "text": "Describe what happens in this video."}
      ]
    }],
    "max_tokens": 1024
  }'
```

## OCR (qwen-vl-ocr)

Use the specialized OCR model for text extraction:

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-vl-ocr",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://img.alicdn.com/imgextra/i2/O1CN01ktT8451iQutqReELT_!!6000000004408-0-tps-689-487.jpg"}},
        {"type": "text", "text": "Read all text in this image."}
      ]
    }],
    "max_tokens": 2048
  }'
```
