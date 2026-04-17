---
name: qwencloud-model-selector
description: "[QwenCloud] Recommend the best Qwen model and parameters. TRIGGER when: choosing between Qwen models, comparing Qwen model pricing, understanding Qwen model capabilities, checking usage or billing, viewing cost history, when an execution skill needs model selection advice, or user explicitly invokes this skill by name (e.g. use qwencloud-model-selector). DO NOT TRIGGER when: non-Qwen model discussions (OpenAI, Gemini, etc.), general AI questions unrelated to Qwen."
compatibility: "Advisory skill, no execution dependencies. Cursor: auto-loaded. Claude Code: read this skill's SKILL.md before first use."
---

> **Agent setup**: If your agent doesn't auto-load skills (e.g. Claude Code),
> see [agent-compatibility.md](references/agent-compatibility.md) once per session.

# Qwen Model Selector (Advisor)

This skill operates in two modes:

1. **Interactive advisory** — asks diagnostic questions to recommend the right model (see Diagnostic Flow).
2. **Cross-skill resolution** — provides a fast-path model lookup for execution skills that need a model decision
   without user interaction (see Cross-Skill Model Resolution).

Do not fabricate model names — only recommend models listed in this skill.
This skill is part of **qwencloud/qwencloud-ai**.

## Skill directory

Use this skill's reference files for data and learning. Load on demand — do not fetch external URLs unless the user
explicitly asks for latest data.

| Location                            | Purpose                                                                               |
|-------------------------------------|---------------------------------------------------------------------------------------|
| `references/pricing.md`             | Pricing overview — model categories, billing units, and link to official pricing page |
| `references/model-list.md`          | Model catalog (point-in-time snapshot)                                                |
| `references/sources.md`             | Official documentation URLs (manual lookup only)                                      |
| `references/agent-compatibility.md` | Agent self-check: register skills in project config for agents that don't auto-load   |

## Security

**NEVER output any API key or credential in plaintext.** Always use variable references (`$DASHSCOPE_API_KEY` in shell,
`os.environ["QWEN_API_KEY"]` in Python). Any check or detection of credentials must be **non-plaintext**: report
only status (e.g. "set" / "not set", "valid" / "invalid"), never the value. Never display contents of `.env` or config
files that may contain secrets.

## Coding Plan Models

Users with a [Coding Plan](https://www.qwencloud.com/pricing/coding-plan) subscription have access to a
limited set of models through their coding tools only:

| Model                | Context | Thinking             |
|----------------------|--------:|----------------------|
| qwen3.5-plus         |      1M | Yes (budget: 81,920) |
| kimi-k2.5            |    256K | Yes (budget: 81,920) |
| glm-5                |    198K | Yes (budget: 32,768) |
| MiniMax-M2.5         |    192K | Yes (budget: 32,768) |
| qwen3-max-2026-01-23 |    256K | Yes (budget: 81,920) |
| qwen3-coder-next     |    256K | No                   |
| qwen3-coder-plus     |      1M | No                   |
| glm-4.7              |    198K | Yes (budget: 32,768) |

Coding Plan does **not** include image, video, TTS, or specialized vision models. When recommending models, note if the
user's chosen model falls outside this list and they are using a Coding Plan key (`sk-sp-...`). If qwencloud-ops-auth is
installed, see its `references/codingplan.md` for the full model list and error codes.

## Diagnostic Flow

Ask the user (in order):

1. **Content type?** — text / image / video / audio / vision
2. **Primary task?** — generation / understanding / coding / reasoning / translation
3. **Priority?** — quality vs speed vs cost
4. **Input size?** — short / medium / long context
5. **Structured output?** — JSON / function calling needed?

## Cross-Skill Model Resolution

When an execution skill needs to choose a model, evaluate across three dimensions: **Requirement → Scenario →
Pricing**. If the user explicitly specified a model, use it as given — but still verify availability; if
restricted, warn the user and suggest an alternative.

### Dimension 1 · Requirement (select)

Match task capability to the right model. Use when the user's need points to a specialized model, or when the task is
ambiguous and you need to compare capabilities.

| Signal                         | Keywords                                          | Model                                                        |
|--------------------------------|---------------------------------------------------|--------------------------------------------------------------|
| Reasoning                      | "think step by step", "reason", "analyze"         | qwq-plus (text) · qvq-max (vision)                           |
| Coding                         | "write code", "implement", "debug"                | qwen3-coder-plus                                             |
| OCR / document                 | "extract text", "OCR", "scan"                     | qwen-vl-ocr                                                  |
| Long context                   | "long document", "large file"                     | qwen3.6-plus (1M context)                                    |
| Multimodal (text+image+video)  | "analyze image", "understand video" + text        | qwen3.6-plus (unified multimodal)                            |
| Voice interaction / omni       | "voice chat", "speak", "listen"                   | qwen3-omni-flash                                             |
| Built-in tools                 | "search the web", "run code", "use tools"         | qwen3-max (web search, code interpreter)                     |
| Image editing / style transfer | "edit image", "style transfer", "reference image" | wan2.6-image (preferred) · wan2.5-i2i-preview                |
| Image-to-image fusion          | "place object", "combine images", "fuse images"   | wan2.6-image · wan2.5-i2i-preview                            |
| Style TTS                      | "emotion", "tone", "pace"                         | qwen3-tts-instruct-flash                                     |
| Ambiguous                      | task doesn't clearly map to one model             | compare Recommendation Matrix; ask user to clarify if needed |

### Dimension 2 · Scenario (tune)

Adjust model tier based on how the model will be used.

| Pattern                 | Signals                                 | Guidance                                                                |
|-------------------------|-----------------------------------------|-------------------------------------------------------------------------|
| Interactive / real-time | "chat", "real-time", "interactive"      | Prefer flash/turbo variants; enable streaming                           |
| Batch / offline         | "batch", "offline", "background"        | Quality model + Batch API (50% off)                                     |
| One-off trial           | "try", "test", "experiment"             | Quality model; use **qwencloud-usage** skill or check console for remaining free quota |
| High-volume production  | "production", "at scale", "high volume" | Cost-optimize: flash/turbo + context cache                              |
| Repeated context        | "template", "same prompt", "repeated"   | Enable context caching for input token discount                         |

### Dimension 3 · Pricing (optimize)

Given the candidates from dimensions 1–2, compare costs and apply modifiers.

- Pricing reference: [pricing.md](references/pricing.md). For the latest rates, check
  the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing).
- **Free quota**: Some models offer a limited free quota after activation. However, quotas may have been consumed,
  expired, or changed. **Never assume remaining free quota** — always present the paid unit price. Use the **qwencloud-usage** skill to check remaining free tier quota.
- **Batch API**: 50% off both input and output tokens for non-realtime workloads.
- **Context cache**: Input token discount for repeated/templated contexts.
- **Tiered pricing**: Some models charge more per token as input length increases — check pricing tables for
  breakpoints.
- When cost is the user's primary concern, explicitly recommend the cheapest viable model and cite the price.

### Default

No signals detected, clear task → use the Canonical Default for the domain.

| Domain              | Default          | Quality          | Speed              | Cost               |
|---------------------|------------------|------------------|--------------------|--------------------|
| text.chat           | qwen3.6-plus     | qwen3-max        | qwen3.5-flash      | qwen-turbo         |
| vision.analyze      | qwen3.6-plus     | qwen3-vl-plus    | qwen3-vl-flash     | qwen3-vl-flash     |
| omni (voice+vision) | qwen3-omni-flash | qwen3-omni-flash | qwen3-omni-flash   | —                  |
| image.generate      | wan2.6-t2i       | wan2.6-t2i       | wan2.2-t2i-flash   | wan2.2-t2i-flash   |
| image.edit          | wan2.6-image     | wan2.6-image     | wan2.5-i2i-preview | wan2.5-i2i-preview |
| video.t2v           | wan2.6-t2v       | wan2.6-t2v       | —                  | —                  |
| video.i2v           | wan2.6-i2v-flash | wan2.6-i2v       | wan2.6-i2v-flash   | —                  |
| audio.tts           | qwen3-tts-flash  | —                | qwen3-tts-flash    | —                  |

> **Degradation**: If this skill is not loaded or not available, each execution skill falls back to its own built-in
> default. This protocol is purely additive — it enhances model selection but never blocks execution.

## Model Recommendation Matrix

### Text Models

| Use Case                 | Recommended      | Why                                                                                                                 |
|--------------------------|------------------|---------------------------------------------------------------------------------------------------------------------|
| General chat/assistant   | qwen3.6-plus     | **Latest flagship.** Best balance of quality, speed, cost. **Also accepts image/video input** (multimodal). Thinking enabled by default. 1M context. |
| Fast responses, low cost | qwen3.5-flash    | 3x faster, 70% cheaper than Plus. Thinking enabled by default.                                                      |
| Highest quality          | qwen3-max        | Strongest reasoning. Built-in tools (web search, code interpreter). Supports thinking mode.                         |
| Code generation          | qwen3-coder-next | Best balance of code quality, speed, cost. Agentic coding. `qwen3-coder-plus` for highest quality.                  |
| Complex reasoning        | qwq-plus         | Chain-of-thought reasoning specialist                                                                               |
| Long documents           | qwen3.6-plus     | Up to 1M context. For >1M needs, see [model-list.md](references/model-list.md).                                     |
| Budget/high volume       | qwen-turbo       | Cheapest per-token cost                                                                                             |

### Image Models

| Use Case                                      | Recommended        | Why                                                                             |
|-----------------------------------------------|--------------------|---------------------------------------------------------------------------------|
| Best quality text-to-image                    | wan2.6-t2i         | Latest model, sync support                                                      |
| Image editing / style transfer (1–4 refs)     | wan2.6-image       | Multi-image composition, subject consistency, 2K output, interleaved text-image |
| Image editing / multi-image fusion (1–3 refs) | wan2.5-i2i-preview | Simpler prompt-based editing, subject consistency, multi-image fusion           |
| Interleaved text-image output (tutorials)     | wan2.6-image       | Mixed text+image generation                                                     |
| Fast iteration                                | wan2.2-t2i-flash   | 50% faster generation                                                           |
| Flexible resolution                           | wan2.5-t2i-preview | Custom aspect ratios                                                            |

### Video Models

| Use Case             | Recommended        | Why                        |
|----------------------|--------------------|----------------------------|
| Quick video creation | wan2.6-i2v-flash   | Fast, multi-shot narrative |
| High quality         | wan2.6-i2v         | Best visual quality        |
| With audio           | wan2.5-i2v-preview | Auto-dubbing support       |

### Audio Models

| Use Case              | Recommended              | Why                                                    |
|-----------------------|--------------------------|--------------------------------------------------------|
| **Highest quality**   | `cosyvoice-v3-plus`      | Best naturalness, emotional expression, professional scenarios |
| High quality + speed  | `cosyvoice-v3-flash`     | Good balance of quality and performance                |
| Standard TTS          | `qwen3-tts-flash`        | Fast, reliable, multi-language, cost-effective         |
| Controlled style      | `qwen3-tts-instruct-flash` | Instruction-guided voice style (tone/emotion)        |

### Vision Models

| Use Case            | Recommended    | Why                                                                                                                            |
|---------------------|----------------|--------------------------------------------------------------------------------------------------------------------------------|
| Best accuracy       | qwen3.6-plus   | **Latest flagship.** Multimodal (text + image + video). Surpasses qwen3-vl series on many benchmarks. Thinking enabled by default. |
| High-precision localization | qwen3-vl-plus | Highest vision understanding for object localization (2D/3D), document/webpage parsing. Thinking mode supported. 256K context. |
| Fast analysis       | qwen3-vl-flash | Quick image understanding. Thinking mode supported.                                                                            |
| Unified text+vision | qwen3.6-plus   | Best when both text quality and vision matter. 1M context.                                                                     |

### Omni Models

| Use Case            | Recommended               | Why                                                                                   |
|---------------------|---------------------------|---------------------------------------------------------------------------------------|
| Voice + vision chat | qwen3-omni-flash          | Text/image/audio/video → text or speech. 49 voices, 10 languages. Thinking supported. |
| Real-time voice     | qwen3-omni-flash-realtime | Streaming audio input + built-in VAD. 49 voices.                                      |

## Model Detail Page

When the user wants to learn more about a specific model (capabilities, specifications, benchmarks, etc.), direct them to the model detail page:

**URL pattern**: `https://www.qwencloud.com/models/<model-name>`

Example: for `qwen3.6-plus`, the URL is `https://www.qwencloud.com/models/qwen3.6-plus`.

> **IMPORTANT**: The `<model-name>` in the URL must exactly match the model ID used in this skill (e.g. `qwen3.6-plus`, `wan2.7-t2v`, `qwen3-tts-flash`). NEVER guess or modify the model name segment.

## Pricing Guidance

- **Default pricing**: [pricing.md](references/pricing.md) — International, USD.
  For the latest rates, check
  the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing).
- **Latest prices**: When the user explicitly asks for exact/latest pricing, see [sources.md](references/sources.md) for
  official URLs.
- **Cost formula**: `Cost = Tokens ÷ 1,000,000 × Unit price`. 1K Chinese chars ≈ 1,200-1,500 tokens.
- **Free quota**: Some models offer a limited free quota after activation — but quotas may have been consumed, expired,
  or changed without notice. **Always present the paid unit price first.** Mention free quota only as something the user
  should verify in their [QwenCloud console](https://home.qwencloud.com/benefits).
- **Cost tips**:
    - Use Batch calling for 50% off in non-realtime scenarios
    - Enable context cache for repeated contexts
    - Use flash/turbo series for non-critical tasks

### Usage & Billing Console

When the user asks about actual usage, spending history, or billing details — direct them to the appropriate console page (these are NOT accessible via API; the user must open them in a browser):

| Question | Console Page |
|----------|--------------|
| "How much have I used?" / "Show my usage" | [Usage Analytics](https://home.qwencloud.com/analytics) |
| "Show my bill" / "How much did I spend?" (pay-as-you-go) | [Pay-as-you-go Billing](https://home.qwencloud.com/billing/pay-as-you-go) |
| "Show my Coding Plan bill" / "Coding Plan usage" | [Coding Plan Billing](https://home.qwencloud.com/billing/coding-plan) |

> **Important**: This skill can estimate costs based on published unit prices, but **cannot** query the user's actual account balance, historical spending, or remaining quota. For real-time account data, always direct the user to the console pages above.

### Cost Estimation Disclaimer (MANDATORY)

> 🚨 **CRITICAL — NO EXCEPTIONS**: **NEVER fabricate, invent, or guess any price figure.** If you do not have a
> confirmed price from `references/pricing.md` or the official pricing page, you **MUST NOT** output any number.
> Instead, direct the user to
> the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing).
> Outputting a made-up price is a **critical failure** — worse than saying "I don't know."

When responding to **any** cost-related query — including but not limited to price evaluation, usage estimation, budget
forecasting, or cost comparison — you **MUST** append a professional disclaimer. This applies regardless of language or
response format.

**Required disclaimer (Chinese response):**

> ⚠️ **费用说明**：以上费用为基于官方公示单价的预估价格，仅供参考。实际费用受 Token
> 消耗量、上下文长度阶梯定价、Batch/缓存折扣及计费策略调整等因素影响，请以QwenCloud控制台的实际账单为准：[按量付费账单](https://home.qwencloud.com/billing/pay-as-you-go) | [Coding Plan 账单](https://home.qwencloud.com/billing/coding-plan) | [用量分析](https://home.qwencloud.com/analytics)。部分模型可能提供限时免费额度，但免费额度的可用性、额度量及有效期随时可能调整，请在控制台确认您的账户是否仍有剩余额度，**切勿假设本次调用免费**。最新定价详见 [模型定价页](https://docs.qwencloud.com/developer-guides/getting-started/pricing)。

**Required disclaimer (English response):**

> ⚠️ **Pricing Notice**: The cost figures above are **estimates** calculated from officially published unit prices and
> are provided for reference only. Actual charges depend on token consumption, tiered context-length pricing,
> Batch/cache discounts, and billing policy updates. Some models may offer a time-limited free quota, but
> quota availability, amounts, and validity periods are subject to change — **do not assume this call is free**. Please
> verify your remaining quota in
> the [QwenCloud console](https://home.qwencloud.com/benefits) and refer to your actual
> bill for definitive costs: [Pay-as-you-go Billing](https://home.qwencloud.com/billing/pay-as-you-go) |
> [Coding Plan Billing](https://home.qwencloud.com/billing/coding-plan) |
> [Usage Analytics](https://home.qwencloud.com/analytics).
> See [Model Pricing](https://docs.qwencloud.com/developer-guides/getting-started/pricing) for
> the latest rates.

**Rules:**

- The disclaimer must appear at the **end** of every cost-related response, clearly separated from the main content.
- When the estimate involves assumptions (e.g., average tokens per character, assumed context length tier), **explicitly
  state each assumption** used in the calculation.
- Never present estimated costs as exact or guaranteed amounts. Use hedging language such as "approximately", "estimated
  at", "roughly" (or Chinese equivalents "约", "预估", "约合") throughout the cost breakdown.
- **Never tell the user a call will be free or cost $0/¥0.** Even if a free quota exists, the user may have already
  consumed it. Always present the paid price and note that a free quota *may* apply — subject to the user verifying in
  their console.
- **If pricing data is unavailable or uncertain, say so explicitly and link to the official pricing page. Never fill
  the gap with a guess.**

## Available Models

All standard text, vision, image, video, audio, and coding models are available. Some models offer free
quota (verify in console).

- **Text**: qwen3.6-plus, qwen3-max, qwen3.5-plus, qwen3.5-flash, qwen-turbo, qwq-plus, qwen3-coder-next/plus/flash, qwen-plus-character, qwen-plus-character-ja, qwen-flash-character
- **Vision**: qwen3.6-plus (multimodal), qwen3-vl-plus, qwen3-vl-flash, qvq-max, qwen-vl-ocr, qwen-vl-max, qwen-vl-plus
- **Omni**: qwen3-omni-flash (+ realtime), qwen-omni-turbo (+ realtime)
- **Image generation (text-to-image)**: wan2.6-t2i, wan2.5-t2i-preview, wan2.2-t2i-flash, z-image-turbo
- **Image editing (requires reference images)**: wan2.6-image, wan2.5-i2i-preview
- **Video generation**: wan2.6 series (t2v, i2v, i2v-flash, r2v, r2v-flash), wan2.5/2.2 series, vace
- **TTS**: qwen3-tts-flash, qwen3-tts-instruct-flash, cosyvoice-v3 series
- **ASR**: qwen3-asr-flash, fun-asr
- **Embedding/Rerank**: text-embedding-v4, qwen3-rerank
- **Translation**: qwen-mt-plus/flash/lite/turbo

> **⚠️ Important**: The model list above is a **point-in-time snapshot** and may be outdated. Model availability
> changes frequently. **Always check the [official model list](https://www.qwencloud.com/models)
> for the authoritative, up-to-date catalog before making model decisions.**
> See [model-list.md](references/model-list.md) for a more detailed local reference.

## Thinking Mode

Several models support hybrid thinking/non-thinking modes:

| Model                               | Thinking Default | Notes                                                                                         |
|-------------------------------------|------------------|-----------------------------------------------------------------------------------------------|
| qwen3.6-plus                        | **On**           | Latest flagship. Thinking enabled by default. Use `enable_thinking: false` to disable.       |
| qwen3.5-plus                        | **On**           | Thinking enabled by default. Use `enable_thinking: false` to disable.                         |
| qwen3.5-flash                       | **On**           | Thinking enabled by default.                                                                  |
| qwen3-max                           | Off              | Use `enable_thinking: true` for complex reasoning. Built-in tools available in thinking mode. |
| qwen-plus / qwen-flash / qwen-turbo | Off              | Hybrid; enable for deeper reasoning at higher output cost.                                    |
| qwen3-vl-plus / qwen3-vl-flash      | Off              | Vision + thinking for complex visual analysis.                                                |
| qwen3-omni-flash                    | Off              | Thinking supported; audio output not available in thinking mode.                              |
| qwq-plus / qvq-max                  | Always on        | Pure reasoning models; CoT always active.                                                     |

**Guidance**: Do not enable thinking by default for simple or conversational tasks — it increases latency and output
token cost. Enable only when the user explicitly asks for deep reasoning or the task requires multi-step analysis.

## Anti-Patterns

- **Only recommend models listed in this skill** — never fabricate model names.
- **When unsure**, use `qwen3.6-plus` as a safe default for text tasks.
- **🚨 NEVER invent or guess any price figure** — only use pricing from `references/pricing.md` or the
  [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing). If the data is not
  available, say so and link to the official page. **Fabricating a price is a critical failure.**
- **Always cite data source** when providing pricing info.
- **Default currency is USD.** Check
  the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing) for the latest rates.
  Writing in Chinese does NOT imply CNY.
- **All cost estimates must include the mandatory disclaimer** — use hedging language ("approximately", "estimated").
  Omitting the disclaimer is a critical violation.
- **Never assume free quota is available** — free quotas may have been consumed, expired, or removed. Never tell the
  user a call will cost $0/¥0. Always present the paid unit price first; mention free quota only as a possibility the
  user should verify in their console.
- **Do NOT proactively fetch URLs or trigger web searches** — only access online sources when the user explicitly asks
  for "latest" data AND reference files cannot answer.
- **Never output API keys in plaintext** — see Security section above.

## Online Information Sources

Reference files in this skill are point-in-time snapshots. For official documentation URLs,
see [sources.md](references/sources.md).

**Do NOT proactively fetch or search online.** Only access online sources when ALL of these conditions are met:

1. The user explicitly asks for "latest", "real-time", or "current" data.
2. The reference files in this skill cannot answer the question.
3. The user confirms they want an online lookup.

## Update Check (MANDATORY Post-Execution)

When the user asks to check for updates (e.g. "check for updates", "check version", "is there a new version", "update
skills"):

1. **Find qwencloud-update-check**: Look for `qwencloud-update-check/SKILL.md` in sibling skill directories.
2. **If found** — run: `python3 <qwencloud-update-check-dir>/scripts/check_update.py --print-response` and report the result.
   Use `--force` if the user asks to force-check.
3. **If not found** — you MUST present the following options and **wait for the user's response**:

> The update-check skill is not installed. It keeps you informed about new qwencloud/qwencloud-ai features and bug fixes.
>
> 1) **Install now** — I'll run the install command for you
> 2) **Skip for now** — do nothing this time
> 3) **Never remind me** — permanently suppress this prompt

After the user responds:

- User chooses **1** → run:
  `npx skills add QwenCloud/qwencloud-ai --skill qwencloud-update-check -y`, then run:
  `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`
- User chooses **2** → run: `python3 <this-skill-scripts-dir>/gossamer.py --dismiss`, then continue normally
- User chooses **3** → run: `python3 <this-skill-scripts-dir>/gossamer.py --never-install`, then continue normally

## References

- [pricing.md](references/pricing.md) — Pricing overview: model categories, billing units, and link to official pricing
  page
- [model-list.md](references/model-list.md) — Model catalog (2026-03 snapshot;
  check [official model list](https://www.qwencloud.com/models) for latest)
- [sources.md](references/sources.md) — Official documentation URLs (for manual lookup only)
