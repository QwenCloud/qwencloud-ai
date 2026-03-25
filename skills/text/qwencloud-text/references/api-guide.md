# Qwen Text Chat — API Supplementary Guide

> **Content validity**: 2026-03 | **Sources**: [OpenAI compatibility](https://docs.qwencloud.com/api-reference/preparation/install-sdk) · [Qwen API](https://docs.qwencloud.com/api-reference/chat/dashscope) · [Function calling](https://docs.qwencloud.com/developer-guides/text-generation/function-calling) · [Models](https://www.qwencloud.com/models)

---

## Definition

Qwen text generation models accessed through an **OpenAI-compatible** interface. Migrate existing OpenAI code by updating three values: `base_url`, `api_key`, and `model`. Supports text generation, multi-turn conversations, code writing, reasoning, and function calling.

---

## Use Cases

| Scenario | Recommended Model | Notes |
|----------|------------------|-------|
| General conversation / content generation | `qwen3.5-plus` | Best balance of performance, cost, and speed. **Recommended default.** |
| Low-latency real-time interaction | `qwen3.5-flash` / `qwen-turbo` | Fastest response time. Suitable for chatbots. |
| Complex tasks / strongest capability | `qwen3-max` | Largest model. Best for complex reasoning. |
| Code generation / completion | `qwen3-coder-next` | Top recommendation. `qwen3-coder-plus` for highest quality, `qwen3-coder-flash` for speed. |
| Deep reasoning / math | `qwq-plus` | Chain-of-thought (CoT) reasoning. |
| Ultra-long document processing | `qwen-long` | 10M token context. Not available in ap-southeast-1. |
| Agent / tool calling | `qwen3.5-plus` / `qwen-plus` | Most complete function calling support. |
| Machine translation | `qwen-mt-plus` | Best quality, 92 languages. `qwen-mt-flash` for speed, `qwen-mt-lite` for real-time chat. Uses `translation_options` parameter. |
| Role-playing / character dialog | `qwen-plus-character-ja` | Character restoration, empathetic dialog. Singapore: use `-ja` variant. |

---

## Key Usage

### Regional Endpoints

| Region | base_url |
|--------|----------|
| Singapore (default) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |

### Non-streaming Call

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
resp = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
)
print(resp.choices[0].message.content)
```

### Streaming (recommended for interactive use)

```python
stream = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[{"role": "user", "content": "Write a haiku."}],
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Function Calling

Workflow: **Define tools → Model returns tool call instruction → Execute tool → Send result back → Get final answer.**

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
}]

resp = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[{"role": "user", "content": "What's the weather in Beijing?"}],
    tools=tools,
)
# resp.choices[0].message.tool_calls contains function name and arguments
# Execute the function, then send result back with role="tool"
```

Supported models: Qwen-Max/Plus/Flash/Turbo, Qwen3.5/3 series, qwen3-vl-plus/flash, qwen3-omni-flash.

### Thinking Mode

**Model defaults apply**: `qwen3.5-plus` and `qwen3.5-flash` have thinking mode **enabled by default**. For these models, do NOT set `enable_thinking` unless you want to override the default behavior.

For other models (`qwen3-max`, `qwen-plus`, `qwen-turbo`, etc.), thinking mode is off by default. Only enable when the user explicitly requests step-by-step reasoning:

```python
# For qwen3.5-plus/flash: thinking is ON by default, no need to set
resp = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[{"role": "user", "content": "Solve this problem."}],
)

# For other models: enable thinking only when user explicitly requests it
resp = client.chat.completions.create(
    model="qwen3-max",
    messages=[{"role": "user", "content": "Solve 17 × 23 step by step."}],
    extra_body={"enable_thinking": True},  # Only for non-default models
)

# Script usage: add --enable-thinking flag to override defaults
# python scripts/text.py --request '{"messages":[...]}' --enable-thinking
```

**When to disable thinking for qwen3.5-plus/flash**: Set `enable_thinking: false` for simple chat, real-time interaction, or when you want faster responses without extended reasoning.

### Key Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | string | **Required.** Model ID. |
| `messages` | array | **Required.** Conversation history. Format: `{"role": "...", "content": "..."}`. Roles: `system`, `user`, `assistant`. `system` can only appear at `messages[0]`. Last element must have `user` role. |
| `temperature` | float | Controls randomness. Range: [0, 2). Higher values produce more diverse output. |
| `top_p` | float | Nucleus sampling threshold. Range: (0, 1.0). |
| `max_tokens` | int | Maximum number of output tokens. |
| `stream` | bool | Enable streaming output. |
| `tools` | array | Tool definitions for function calling. |
| `stop` | string/array | Stop generation when specified string or token is about to be output. |

### Key Response Fields

| Field | Description |
|-------|-------------|
| `choices[0].message.content` | Generated text. |
| `choices[0].message.tool_calls` | Tool call instructions (if applicable). |
| `choices[0].finish_reason` | `stop` = normal completion; `length` = max_tokens reached. |
| `usage.prompt_tokens` / `completion_tokens` | Token consumption. |

---

## Important Notes

1. **Prefer streaming.** Non-streaming blocks until the full response is generated (10–60s+ for long outputs). Always use `stream=True` for interactive scenarios.
2. **API keys are region-specific.** Use the `ap-southeast-1` (Singapore) endpoint with your API key.
3. **openai SDK version:** Requires ≥1.55.0. Older versions conflict with httpx ≥0.28, causing a `proxies` TypeError.
4. **Thinking mode varies by model.** `qwen3.5-plus` and `qwen3.5-flash` have thinking mode enabled by default; other models have it off. Only override with `enable_thinking` when you want to change the default behavior.
5. **Function calling constraints.** `tools` cannot be used with `stream=True` (older limitation; some newer models support it). Also incompatible with `n > 1`.
6. **messages format.** `system` role can only appear at `messages[0]`. The last message must have the `user` role.
7. **Some models have limited regional availability.** `qwen-long` (10M context), `qwen-math-plus`, and third-party
   models are not available in `ap-southeast-1`. Check
   the [Model List](https://www.qwencloud.com/models) for the latest availability.

---

## FAQ

**Q: How do I migrate from OpenAI?**
A: Change three values: `api_key` to your DASHSCOPE_API_KEY, `base_url` to the corresponding regional endpoint, and `model` to a Qwen model name. All other code remains compatible.

**Q: When should I use streaming vs. non-streaming?**
A: Use streaming for interactive scenarios (chat, real-time output). Use non-streaming for batch processing or when you need the complete JSON response at once. With streaming, set `stream_options={"include_usage": True}` to receive token usage in the last chunk.

**Q: Which models support function calling?**
A: Qwen-Max/Plus/Flash/Turbo series, Qwen3.5/3/2.5 series, qwen3-vl-plus/flash, qwen3-omni-flash, and third-party models (deepseek, kimi, glm).

**Q: What is the difference between `qwen3.5-plus` and `qwen-plus`?**
A: `qwen3.5-plus` is the latest commercial model with 1M context and stronger performance. `qwen-plus` is the previous stable version. `qwen3.5-plus` is recommended for new projects.

**Q: How do I control output length?**
A: Use `max_tokens` to limit output token count. Use `stop` to set stop sequences. Each model has its own default output limit.

**Q: What should I do when I get a 429 error?**
A: 429 indicates QPS/QPM rate limit exceeded or insufficient quota. Implement exponential backoff retry, or check remaining quota in the console.
