# Coding Plan vs Standard API Key

> Sources:
> - https://www.qwencloud.com/pricing/coding-plan
> - https://docs.qwencloud.com/coding-plan/overview
> Updated: 2026-03-11

## Two Key Types

Alibaba Cloud Model Studio has two mutually exclusive authentication systems. Mixing them produces hard-to-diagnose errors.

| Dimension | Standard Key (Pay-as-you-go) | Coding Plan |
|-----------|------------------------------|-------------|
| Key format | `sk-xxxxx` | `sk-sp-xxxxx` |
| OpenAI-compatible URL | `dashscope-intl.aliyuncs.com/compatible-mode/v1` | `coding-intl.dashscope.aliyuncs.com/v1` |
| Anthropic-compatible URL | N/A | `coding-intl.dashscope.aliyuncs.com/apps/anthropic` |
| Native DashScope URL | `dashscope-intl.aliyuncs.com/api/v1` | **Not supported** |
| Supported models | Full catalog (100+ across text, vision, image, video, audio) | 8 text-only models (see below) |
| Usage scope | Any API call (scripts, apps, tools) | **Coding tools only** (Cursor, Claude Code, Qwen Code, etc.) |
| Billing | Per-token consumption | Monthly subscription (see [Coding Plan pricing](https://www.qwencloud.com/pricing/coding-plan)) |
| Quota exhaustion | Continues (pay more or use prepaid balance) | **Hard fail — no fallback to pay-as-you-go** |
| Image/Video/TTS models | All available | **None** |

## Coding Plan Supported Models

| Model | Context Window | Thinking Mode | Max Thinking Budget |
|-------|---------------|---------------|--------------------:|
| qwen3.5-plus | 1,000,000 | Yes | 81,920 |
| kimi-k2.5 | 256,000 | Yes | 81,920 |
| glm-5 | 198,000 | Yes | 32,768 |
| MiniMax-M2.5 | 192,000 | Yes | 32,768 |
| qwen3-max-2026-01-23 | 256,000 | Yes | 81,920 |
| qwen3-coder-next | 256,000 | **No** | N/A |
| qwen3-coder-plus | 1,000,000 | **No** | N/A |
| glm-4.7 | 198,000 | Yes | 32,768 |

### Quota Limits

For current quota limits by plan tier, see the [Coding Plan documentation](https://www.qwencloud.com/pricing/coding-plan).
## Key Type x Endpoint — Expected Behavior

| Key Type | Base URL | Result |
|----------|----------|--------|
| `sk-` | `dashscope-intl.aliyuncs.com/...` | OK |
| `sk-` | `coding-intl.dashscope.aliyuncs.com/...` | **401** — regular key rejected |
| `sk-sp-` | `dashscope-intl.aliyuncs.com/...` | **403** — Coding Plan key rejected |
| `sk-sp-` | `coding-intl.dashscope.aliyuncs.com/...` | **Agent context required** — rejects non-agent scripts |

## Error Codes

| Error | Cause | Resolution |
|-------|-------|------------|
| `401 invalid access token` | `sk-` on coding-intl endpoint, or expired subscription | Use plan-specific key; check subscription status |
| `403 invalid api-key` | `sk-sp-` on standard DashScope endpoint | Use a standard key for scripts |
| `model 'xxx' is not supported` | Model not in Coding Plan list (case-sensitive) | Check model IDs above |
| `Coding Plan is currently only available for Coding Agents` | Script/curl calling coding-intl | Use through coding tools only, not scripts |
| `hour/week/month allocated quota exceeded` | Plan quota exhausted | Wait for reset or upgrade |

## Impact on qwencloud/qwencloud-ai Scripts

All scripts call DashScope directly via `urllib.request` and are **not** recognized as coding agents. Scripts detect `sk-sp-` keys and print a warning to stderr.

| Skill | API Type | Works with sk-sp-? | Reason |
|-------|----------|:------------------:|--------|
| qwencloud-text | OpenAI-compat | No | 403 on standard endpoint; scripts are not coding agents |
| qwencloud-vision | OpenAI-compat | No | Same; vision models not in Coding Plan |
| qwencloud-image-generation | Native | No | Native endpoint not supported; image models unavailable |
| qwencloud-video-generation | Native | No | Same; video models unavailable |
| qwencloud-audio-tts | Native | No | Same; TTS models unavailable |

## Cost Risk Scenarios

1. **sk-sp- key in scripts**: 403 error, no charges, but confusing. Scripts warn on detection.
2. **sk- key when user expects Coding Plan coverage**: Calls succeed but incur pay-as-you-go charges. Cannot detect programmatically — documentation must clarify.
3. **QWEN_BASE_URL set to coding-intl**: "Coding Plan is currently only available for Coding Agents". Scripts warn on detection.
4. **Coding Plan quota exhausted**: Hard fail, no fallback. Users must wait for reset or upgrade.

To verify actual charges, direct users to the appropriate billing page:
- Pay-as-you-go: [Pay-as-you-go Billing](https://home.qwencloud.com/billing/pay-as-you-go)
- Coding Plan: [Coding Plan Billing](https://home.qwencloud.com/billing/coding-plan)
- Usage analytics: [Usage Analytics](https://home.qwencloud.com/analytics)

## Resolution

Both key types can coexist. A user can have:
- Coding Plan key (`sk-sp-`) for their IDE coding agent (Cursor, Claude Code)
- Standard key (`sk-`) for API scripts in qwencloud/qwencloud-ai

Set the standard key in `DASHSCOPE_API_KEY` when using these skills.
