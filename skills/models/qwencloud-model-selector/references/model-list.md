# Bailian Model List

> Source: https://www.qwencloud.com/models
> Updated: 2026-04-03

## Text Generation — Commercial

| Model ID          | Context                             | Thinking         | Key Info                                                                                                                           |
|-------------------|-------------------------------------|------------------|------------------------------------------------------------------------------------------------------------------------------------|
| qwen3-max         | 256K                                | Yes (hybrid)     | Strongest. Built-in tools (web search, code interpreter). Tiered pricing.                                                          |
| qwen3.6-plus      | 1M                                  | Yes (default on) | **Latest flagship.** Multimodal (text + image + video). Best balance of quality, speed, cost. Surpasses qwen3-vl series. Tiered pricing. |
| qwen3.5-plus      | 1M                                  | Yes (default on) | Multimodal (text + image + video input). On par with qwen3-max for text; surpasses qwen3-vl series for vision. Tiered pricing. |
| qwen3.5-flash     | 1M                                  | Yes (default on) | Fastest Qwen3.5. Tiered pricing.                                                                                                   |
| qwen-plus         | 1M                                  | Yes (hybrid)     | General purpose (Qwen3 series). Tiered pricing.                                                                                    |
| qwen-flash        | 1M                                  | Yes (hybrid)     | Economy. Tiered pricing. Context cache supported.                                                                                  |
| qwen-turbo        | 1M (non-thinking) / 128K (thinking) | Yes (hybrid)     | Cheapest per-token.                                                                                                                |
| qwq-plus          | 128K                                | Always-on CoT    | Reasoning specialist. Max CoT 32K, response 8K.                                                                                    |
| qwen3-coder-next  | 256K                                | No               | Top code recommendation. Balances quality, speed, cost. Agentic coding, multi-turn tool calling.                                   |
| qwen3-coder-plus  | 1M                                  | No               | Best code model. Tiered pricing. Context cache supported.                                                                          |
| qwen3-coder-flash | 1M                                  | No               | Fast code model. Tiered pricing.                                                                                                   |
| qwen-plus-character-ja | 32K                            | No               | Role-playing, Japanese. Recommended for Singapore.                                                                                 |
| qwen-plus-character | 32K                               | No               | Role-playing, character restoration, empathetic dialog.                                                                            |
| qwen-flash-character | 8K                               | No               | Role-playing, fast, lower cost.                                                                                                    |

## Vision — Commercial

| Model ID | Context | Thinking | Key Info |
|----------|---------|----------|----------|
| qwen3-vl-plus | 256K | Yes (hybrid) | Best vision. Tiered pricing. Context cache supported. Max 16K tokens/image. |
| qwen3-vl-flash | 256K | Yes (hybrid) | Fast vision. Tiered pricing. Context cache supported. |
| qvq-max | 128K | Always-on CoT | Visual reasoning (math, charts). Max CoT 16K, response 8K. |
| qwen-vl-ocr | 38K | No | OCR specialist. Max 30K tokens/image. |
| qwen-vl-max | 131K | No | Best in Qwen2.5-VL series. |
| qwen-vl-plus | 131K | No | Qwen2.5-VL. Faster, good balance, 11 languages. |

## Omni — Commercial

| Model ID | Context | Thinking | Key Info |
|----------|---------|----------|----------|
| qwen3-omni-flash | 128K | Yes (hybrid) | Text/image/audio/video → text or speech. 49 voices, 10 languages. |
| qwen-omni-turbo | 32K | No | Legacy omni, max 2K output. Use qwen3-omni-flash instead. |
| qwen3-omni-flash-realtime | 128K | No | Streaming audio input + VAD. 49 voices, 10 languages. |
| qwen-omni-turbo-realtime | 32K | No | Legacy realtime. Use qwen3-omni-flash-realtime instead. |

## Translation — Commercial

| Model ID | Context | Key Info |
|----------|---------|----------|
| qwen-mt-plus | 16K | Highest quality. 92 languages. |
| qwen-mt-flash | 16K | Fast. |
| qwen-mt-lite | 16K | Cheapest. |
| qwen-mt-turbo | 16K | Balanced. |

## Image Generation

| Model ID | Key Info |
|----------|----------|
| wan2.7-image-pro | **Multi-function** (4K support) — text-to-image, image editing (0–9 images), sequential multi-image, interactive editing (bbox), thinking mode, color palette. Max 4K for t2i, 2K for editing |
| wan2.7-image | **Multi-function** (faster) — same as pro but max 2K, no 4K support |
| wan2.6-t2i | Text-to-image, sync+async, best quality in wan2.6 series |
| wan2.6-image | Image **editing** (NOT for pure text-to-image): style transfer, subject consistency (1–4 refs), interleaved text-image output, 2K. Requires reference_images or enable_interleave=true |
| wan2.5-i2i-preview | Image editing: single-image editing, multi-image fusion (1–3 refs), subject consistency, async-only |
| wan2.5-t2i-preview | Flexible resolution text-to-image |
| wan2.2-t2i-flash | Fast text-to-image |
| wan2.2-t2i-plus | Quality text-to-image |
| qwen-image-2.0-pro | Fused generation + editing, text rendering, multi-image (1–3 input, 1–6 output) |
| qwen-image-2.0 | Accelerated generation + editing |
| qwen-image-edit-max | Image editing, 1–6 output images |
| qwen-image-edit-plus | Image editing, 1–6 output images |
| qwen-image-edit | Image editing, 1 output image only |
| qwen-image-plus | Text-to-image, fixed resolutions, async only |
| qwen-image-max | Text-to-image, fixed resolutions |

## Video Generation

| Model ID | Key Info |
|----------|----------|
| wan2.7-t2v | Text-to-video, ratio control, auto-dubbing, 5000 char prompt, 720P/1080P |
| wan2.7-i2v | Image-to-video, unified media[] protocol: first/last frame, video continuation, audio sync |
| wan2.6-t2v | Text-to-video, audio, multi-shot, 2–15s |
| wan2.6-i2v / i2v-flash | Image-to-video, audio, multi-shot, 2–15s |
| wan2.6-r2v / r2v-flash | Reference-based, multi-character, 2–10s |
| wan2.2-kf2v-flash | First+last frame, 5s, silent |
| wan2.1-vace-plus | Video editing (repainting, extension, outpainting), ≤5s, silent |

## TTS / ASR

| Model ID | Key Info |
|----------|----------|
| qwen3-tts-flash | Fast multi-language TTS |
| qwen3-tts-instruct-flash | Instruction-controlled TTS |
| qwen3-asr-flash | Real-time ASR |

## Embedding / Rerank

| Model ID | Key Info |
|----------|----------|
| text-embedding-v4 | Text embedding |
| qwen3-rerank | Reranking |

> **⚠️ Important**: The model list above is a **point-in-time snapshot** and may be outdated. Model availability
> changes frequently. **Always check the [official model list](https://www.qwencloud.com/models)
> for the authoritative, up-to-date catalog before making model decisions.**