# CosyVoice TTS Guide

CosyVoice models use **WebSocket API** (not HTTP REST), requiring the DashScope SDK.

## Prerequisites

- **DashScope SDK** (venv recommended):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install dashscope>=1.24.6
  ```
- **API Key**: Same as Qwen TTS (`DASHSCOPE_API_KEY` or `QWEN_API_KEY`)

## Run Script

**Discovery:** `python3 <this-skill-dir>/scripts/tts_cosyvoice.py --help`

```bash
python3 scripts/tts_cosyvoice.py --text "Hello, world!"
```

| Argument | Description |
|----------|-------------|
| `--text`, `-t` | **Required** — text to synthesize |
| `--model`, `-m` | Model ID (default: `cosyvoice-v3-flash`) |
| `--voice`, `-v` | Voice ID (default: `longanyang`) |
| `--output`, `-o` | Output file (default: `output/qwencloud-audio-tts/cosyvoice.mp3`) |
| `--format`, `-f` | Audio format: mp3, wav, pcm (default: mp3) |

## Available Voices

| Voice | Description |
|-------|-------------|
| longanyang | Sunny young man (male) |
| longanhuan | Energetic cheerful female |
| longhuhu_v3 | Innocent lively girl |

> See [voice-list](https://docs.qwencloud.com/api-reference/speech-synthesis/voice-list) for full list.

## Examples

```bash
# Basic synthesis
python3 scripts/tts_cosyvoice.py -t "Hello, world!"

# Chinese with specific voice
python3 scripts/tts_cosyvoice.py -t "你好世界" -v longanhuan

# Highest quality model
python3 scripts/tts_cosyvoice.py -t "Professional narration" -m cosyvoice-v3-plus

# Multiple files (use --output to avoid overwriting)
python3 scripts/tts_cosyvoice.py -t "First sentence" -o output/qwencloud-audio-tts/part1.mp3
python3 scripts/tts_cosyvoice.py -t "Second sentence" -o output/qwencloud-audio-tts/part2.mp3
```

> **Tip**: Default output overwrites previous file. Use `-o` with different filenames for batch tasks.

## Error Handling

| Error Pattern | Resolution |
|---------------|------------|
| `dashscope SDK not installed` | Run `pip install dashscope>=1.24.6` |
| `WebSocket connection failed` | Check network; verify API key |
| `Invalid voice` | Use CosyVoice voices, not Qwen TTS voices (Cherry, Ethan, etc.) |
