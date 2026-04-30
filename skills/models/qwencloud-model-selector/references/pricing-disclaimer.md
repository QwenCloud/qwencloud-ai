# Pricing Guidance & Cost Estimation Disclaimer

This file holds the full pricing guidance, the **mandatory** cost-estimation disclaimer (in both Chinese and
English), and the usage/billing console reference. SKILL.md keeps only a one-line pointer; whenever you produce
a cost-related answer, **you must read and apply this file**.

## Pricing Guidance

- **Default pricing reference**: [pricing.md](pricing.md) — International, USD; structural overview only.
- **Latest / exact prices**: When the user asks for exact or latest pricing, run
  `qwencloud models info <model> --format json` first (returns structured pricing tiers).
  Fall back to the [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing)
  only if CLI is unavailable. **Never invent a number.**
- **Cost formula**: `Cost = Tokens ÷ 1,000,000 × Unit price`. 1K Chinese chars ≈ 1,200–1,500 tokens.
- **Free quota**: Some models offer a limited free quota after activation — but quotas may have been consumed,
  expired, or changed without notice. **Always present the paid unit price first.** Mention free quota only as
  something the user should verify in their [QwenCloud console](https://home.qwencloud.com/benefits) or via
  `qwencloud usage free-tier --format json`.
- **Cost tips**:
    - Use Batch API for 50% off in non-realtime scenarios
    - Enable context cache for repeated contexts
    - Use flash/turbo series for non-critical tasks
    - Watch for tiered pricing breakpoints (≤32K, ≤128K, ≤256K, ≤1M)

## Usage & Billing Console

When the user asks about actual usage, spending history, or billing details — direct them to the appropriate
console page (these are **NOT** accessible via API; the user must open them in a browser):

| Question                                                | Console Page |
|---------------------------------------------------------|--------------|
| "How much have I used?" / "Show my usage"               | [Usage Analytics](https://home.qwencloud.com/analytics) |
| "Show my bill" / "How much did I spend?" (pay-as-you-go)| [Pay-as-you-go Billing](https://home.qwencloud.com/billing/pay-as-you-go) |
| "Show my Coding Plan bill" / "Coding Plan usage"        | [Coding Plan Billing](https://home.qwencloud.com/billing/coding-plan) |

> **Important**: This skill can estimate costs based on published unit prices, but **cannot** query the user's
> actual account balance, historical spending, or remaining quota. For real-time account data, always direct
> the user to the console pages above.
>
> **NEVER fabricate, guess, or construct usage/billing/console URLs.** Only provide the exact links listed in
> this skill. If a URL is not listed here, do not invent one.

## Cost Estimation Disclaimer (MANDATORY)

> 🚨 **CRITICAL — NO EXCEPTIONS**: **NEVER fabricate, invent, or guess any price figure.** If you do not have
> a confirmed price from CLI (`qwencloud models info`), `pricing.md`, or the official pricing page, you
> **MUST NOT** output any number. Instead, direct the user to the
> [official pricing page](https://docs.qwencloud.com/developer-guides/getting-started/pricing).
> Outputting a made-up price is a **critical failure** — worse than saying "I don't know."

When responding to **any** cost-related query — including but not limited to price evaluation, usage
estimation, budget forecasting, or cost comparison — you **MUST** append a professional disclaimer.
This applies regardless of language or response format.

### Required disclaimer (Chinese response)

> ⚠️ **费用说明**：以上费用为基于官方公示单价的预估价格，仅供参考。实际费用受 Token
> 消耗量、上下文长度阶梯定价、Batch/缓存折扣及计费策略调整等因素影响，请以QwenCloud控制台的实际账单为准：[按量付费账单](https://home.qwencloud.com/billing/pay-as-you-go) | [Coding Plan 账单](https://home.qwencloud.com/billing/coding-plan) | [用量分析](https://home.qwencloud.com/analytics)。部分模型可能提供限时免费额度，但免费额度的可用性、额度量及有效期随时可能调整，请在控制台确认您的账户是否仍有剩余额度，**切勿假设本次调用免费**。最新定价详见 [模型定价页](https://docs.qwencloud.com/developer-guides/getting-started/pricing)。

### Required disclaimer (English response)

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

### Rules

- The disclaimer must appear at the **end** of every cost-related response, clearly separated from the main content.
- When the estimate involves assumptions (e.g., average tokens per character, assumed context length tier),
  **explicitly state each assumption** used in the calculation.
- Never present estimated costs as exact or guaranteed amounts. Use hedging language such as "approximately",
  "estimated at", "roughly" (or Chinese equivalents "约", "预估", "约合") throughout the cost breakdown.
- **Never tell the user a call will be free or cost $0/¥0.** Even if a free quota exists, the user may have
  already consumed it. Always present the paid price and note that a free quota *may* apply — subject to the
  user verifying in their console.
- **If pricing data is unavailable or uncertain, say so explicitly and link to the official pricing page.
  Never fill the gap with a guess.**
- **Default currency is USD.** Writing in Chinese does NOT imply CNY. Check the official pricing page for
  the latest rates and currency.
