# Qwen-VL-OCR Text Extraction Guide

> **Content validity**: 2026-03 | **Source**: [Qwen-VL-OCR](https://docs.qwencloud.com/developer-guides/multimodal/ocr)

---

## Overview

Qwen-VL-OCR is optimized for text extraction and structured data parsing from images: scanned documents, tables, receipts, tickets, ID cards, and handwritten text. Higher accuracy than general VL models for text-heavy images.

---
## Supported Models

| Model | Region | Notes |
|-------|--------|-------|
| `qwen-vl-ocr` (stable) | International (ap-southeast-1) | For pricing, see [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing) |
| `qwen-vl-ocr-2025-11-20` | International (ap-southeast-1) | Pinned version |

Context: 38,192 tokens. Max input: 30,000 tokens per image. Max output: 8,192 tokens.

---

## API Reference

Same endpoint: `POST /compatible-mode/v1/chat/completions`

### Pixel Control Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_pixels` | int | Minimum pixel threshold. Default: `32*32*3` (3,072). Controls minimum resolution. |
| `max_pixels` | int | Maximum pixel threshold. Default: `32*32*8192` (8,388,608). Controls max tokens consumed. |

Pass these inside the `image_url` object:

```json
{
  "type": "image_url",
  "image_url": {
    "url": "https://example.com/document.jpg",
    "min_pixels": 3072,
    "max_pixels": 8388608
  }
}
```

### Token Calculation

For `qwen-vl-ocr-2025-11-20`, `token_pixels = 32*32 = 1024`. Formula:

```
tokens = (h_bar × w_bar) / token_pixels + 2
```

Where `h_bar` and `w_bar` are the image dimensions after resizing to fit within pixel bounds.

### Default Behavior

If no prompt is provided, the model uses: *"Please output only the text content from the image without any additional descriptions or formatting."*

---

## Code Examples

### Basic OCR (Python)

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    model="qwen-vl-ocr",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {
                "url": "https://example.com/document.jpg",
                "min_pixels": 3072,
                "max_pixels": 8388608,
            }},
            {"type": "text", "text": "Extract all text from this image."},
        ],
    }],
)
print(completion.choices[0].message.content)
```

### Structured Extraction — Train Ticket (Python)

```python
PROMPT = """Extract the following fields from this train ticket image and return as JSON:
{"invoice_number": "...", "train_number": "...", "departure_station": "...",
 "destination_station": "...", "departure_time": "...", "seat": "...",
 "ticket_price": "...", "passenger_name": "..."}"""

completion = client.chat.completions.create(
    model="qwen-vl-ocr-2025-11-20",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {
                "url": "https://example.com/ticket.jpg",
                "min_pixels": 3072,
                "max_pixels": 8388608,
            }},
            {"type": "text", "text": PROMPT},
        ],
    }],
)
print(completion.choices[0].message.content)
```

### curl

```bash
curl -X POST https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-vl-ocr",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://example.com/doc.jpg", "min_pixels": 3072, "max_pixels": 8388608}},
        {"type": "text", "text": "Extract all text from this image."}
      ]
    }]
  }'
```

---

## Capabilities

- **Multi-language**: Chinese, English, Japanese, Korean, and many more
- **Skewed images**: Automatic rotation correction (DashScope SDK)
- **Tables**: Structured table data extraction
- **Formulas**: Mathematical formula recognition
- **Text localization**: Bounding box coordinates for detected text regions
- **Documents**: Receipts, invoices, ID cards, contracts, handwritten notes

---

## Important Notes

1. **Use qwen-vl-ocr for text-heavy images.** General VL models (qwen3-vl-plus) handle OCR but with lower accuracy on dense text.
2. **Pixel parameters control cost.** Higher `max_pixels` = more tokens = better accuracy but higher cost. For simple text, lower values suffice.
3. **SDK version requirements**: DashScope Python SDK >= 1.22.2, Java SDK >= 2.21.8.
4. **DashScope-only features**: Image rotation correction and built-in OCR task types are only available through the DashScope native API, not through the OpenAI-compatible API.
