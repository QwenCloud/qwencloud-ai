# Qwen Audio TTS — Execution Guide

Fallback paths when the bundled script (Path 1) fails or is unavailable.

## Path 0 · Environment Fix

When the script fails due to environment issues (not API errors):

1. **`python3` not found**: Try `python --version` or `py -3 --version`. Use whichever returns 3.9+. If none work, help the user install Python 3.9+ from https://www.python.org/downloads/.
2. **Version too low** (`Python 3.9+ required` or `SyntaxError`): Install Python 3.9+ alongside existing Python, then use `python3.9` or `python3.11` explicitly.
3. **SSL errors** (`CERTIFICATE_VERIFY_FAILED`): On macOS, run `/Applications/Python\ 3.x/Install\ Certificates.command`. On Linux/Windows, set `SSL_CERT_FILE` to point to your CA bundle.
4. **Proxy**: Set `HTTPS_PROXY=http://proxy:port` before running the script.

After fixing, retry the script (Path 1). If the environment is unfixable, fall through to **Path 2 (curl)** below — curl is available on most systems without Python.

## Path 2 · Direct API Call (curl)

### Standard TTS

**Step 1 — Synthesize speech:**

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-tts-flash",
    "input": {
      "text": "Hello, this is a test.",
      "voice": "Cherry",
      "language_type": "English"
    }
  }'
```

**Step 2 — Extract audio URL** from `output.audio.url`:

```json
{
  "output": {
    "audio": {
      "url": "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/...",
      "format": "wav",
      "sample_rate": 24000
    }
  },
  "usage": {"characters": 25}
}
```

**Step 3 — Download the audio file** (URL valid 24 hours):

```bash
curl -o output.wav "AUDIO_URL_FROM_STEP_2"
```

### With instruction control (qwen3-tts-instruct-flash)

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-tts-instruct-flash",
    "input": {
      "text": "Hello, this is a test.",
      "voice": "Cherry",
      "instructions": "Warm and calm tone, slightly slower pace.",
      "optimize_instructions": true
    }
  }'
```

### Streaming (Base64 audio chunks via SSE)

```bash
curl -sS --no-buffer -X POST "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-DashScope-SSE: enable" \
  -d '{
    "model": "qwen3-tts-flash",
    "input": {
      "text": "Hello, this is a test.",
      "voice": "Cherry"
    }
  }'
```

Each SSE event contains a Base64-encoded audio chunk. Decode and concatenate to build the full audio file.

### Region endpoints
| Region | Base URL |
|--------|----------|
| Singapore (default) | `https://dashscope-intl.aliyuncs.com/api/v1` |
## Paths 3–5 · Fallback Cascade

When agent-executed paths (1–2) fail or shell is restricted:

**Path 3 — Generate Python script**: Read `scripts/tts.py` to understand the API logic. Write a self-contained Python script (stdlib `urllib`) tailored to the user's task. Present it for the user to save and run. Use `os.environ["DASHSCOPE_API_KEY"]` — never hardcode or expose the key.

**Path 4 — Generate curl commands**: Customize the curl templates from Path 2 with the user's specific parameters. Present as ready-to-copy commands.

**Path 5 — Autonomous resolution**: Read `scripts/tts.py` source and `references/*.md` to understand the full API contract. Reason about alternative approaches and implement.

If dependency errors occur: `python3 -m venv .venv && source .venv/bin/activate && pip install <package>`.
