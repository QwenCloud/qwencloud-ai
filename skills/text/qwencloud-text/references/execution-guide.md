# Qwen Text Chat — Execution Guide

Fallback paths when the bundled script (Path 1) fails or is unavailable.

## Path 0 · Environment Fix

When the script fails due to environment issues (not API errors):

1. **`python3` not found**: Try `python --version` or `py -3 --version`. Use whichever returns 3.9+. If none work, help the user install Python 3.9+ from https://www.python.org/downloads/.
2. **Version too low** (`Python 3.9+ required` or `SyntaxError`): Install Python 3.9+ alongside existing Python, then use `python3.9` or `python3.11` explicitly.
3. **SSL errors** (`CERTIFICATE_VERIFY_FAILED`): On macOS, run `/Applications/Python\ 3.x/Install\ Certificates.command`. On Linux/Windows, set `SSL_CERT_FILE` to point to your CA bundle.
4. **Proxy**: Set `HTTPS_PROXY=http://proxy:port` before running the script.

After fixing, retry the script (Path 1). If the environment is unfixable, fall through to **Path 2 (curl)** below — curl is available on most systems without Python.

## Path 2 · Direct API Call (curl)

**Non-streaming** — single request, full response:

```bash
curl -sS -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Response**: Extract the generated text from `choices[0].message.content`:

```json
{
  "choices": [{"message": {"role": "assistant", "content": "Hello! How can I help you?"}}],
  "usage": {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28}
}
```

**Streaming** — tokens arrive incrementally, recommended for interactive use:

```bash
curl -sS --no-buffer -X POST "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3.5-plus",
    "messages": [{"role": "user", "content": "Write a haiku."}],
    "stream": true
  }'
```

Each SSE chunk contains `choices[0].delta.content` with partial text.

**Region endpoints** (replace base URL as needed):

| Region | Base URL |
|--------|----------|
| Singapore (default) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |

## Paths 3–5 · Fallback Cascade

When agent-executed paths (1–2) fail or shell is restricted:

**Path 3 — Generate Python script**: Read `scripts/text.py` to understand the API logic. Write a self-contained Python script (stdlib `urllib` or OpenAI SDK) tailored to the user's task. Present it for the user to save and run. Use `os.environ["DASHSCOPE_API_KEY"]` — never hardcode or expose the key.

OpenAI SDK example:

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
)
print(response.choices[0].message.content)
```

Requires `pip install openai>=1.55.0` — use a venv if dependency conflicts occur: `python3 -m venv .venv && source .venv/bin/activate && pip install openai>=1.55.0`.

**Path 4 — Generate curl commands**: Customize the curl templates from Path 2 with the user's specific parameters. Present as ready-to-copy commands.

**Path 5 — Autonomous resolution**: Read `scripts/text.py` source and `references/*.md` to understand the full API contract. Reason about alternative approaches and implement.

## Function Calling

Pass `tools` with function definitions:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[{"role": "user", "content": "What is the weather in Beijing?"}],
    tools=tools,
)
# Check response.choices[0].message.tool_calls for function invocations
```

## Thinking Mode

Qwen3.5 models support `enable_thinking` for extended reasoning. When enabled, the model may return thinking content before the final answer. **Do not enable by default** — only set `enable_thinking: true` when the user explicitly asks for deep thinking, step-by-step reasoning, or chain-of-thought. Keeping it off improves response speed for simple or conversational requests.

```python
response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[{"role": "user", "content": "Solve: 17 * 23 step by step."}],
    extra_body={"enable_thinking": True},
)
```

Via curl, add `"enable_thinking": true` to the request body.
