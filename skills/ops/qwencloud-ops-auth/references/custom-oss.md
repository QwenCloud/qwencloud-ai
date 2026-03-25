# Custom OSS Storage for File Uploads

By default, local files are uploaded to DashScope temporary storage (`oss://` URLs, 48-hour TTL). For production use, you can configure your own Alibaba Cloud OSS bucket to store uploaded files with no expiration and no rate limits.

> **Warning — Default temp storage is NOT for production:**
> - Temporary URLs expire after **48 hours** and cannot be renewed.
> - The upload policy endpoint is rate-limited to **100 QPS** (per account + model) and cannot be increased.
> - For production, high-concurrency, or load-testing scenarios, use your own OSS bucket as described below.

## Prerequisites

Install the Alibaba Cloud OSS SDK (Python):

```bash
pip install alibabacloud-oss-v2
```

You need an existing OSS bucket. Create one in the [OSS Console](https://oss.console.alibabacloud.com/) if you don't have one.

## Environment Variables

Set `QWEN_TMP_OSS_BUCKET` to activate custom OSS mode. All variables use the `QWEN_TMP_OSS_` prefix.

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `QWEN_TMP_OSS_BUCKET` | Yes (trigger) | OSS bucket name | e.g. `do-not-use-this-name-my-ai-assets` |
| `QWEN_TMP_OSS_REGION` | Yes | OSS region | `ap-southeast-1` |
| `QWEN_TMP_OSS_AK_ID` | No* | AccessKey ID for OSS | `Lxxxxx...` |
| `QWEN_TMP_OSS_AK_SECRET` | No* | AccessKey Secret for OSS | `xxxxx` |
| `QWEN_TMP_OSS_PREFIX` | No | Object key prefix (default: `qwencloud-uploads`) | `ai/prod` |
| `QWEN_TMP_OSS_ENDPOINT` | No | Custom endpoint (overrides region) | `qwc-ai-test-sg.oss-ap-southeast-1.aliyuncs.com` |
| `QWEN_TMP_OSS_URL_EXPIRES` | No | Presigned URL expiry in seconds (default: 86400 = 24h) | `3600` |

### Credential Priority

1. **`QWEN_TMP_OSS_AK_ID` + `QWEN_TMP_OSS_AK_SECRET`** — used if both are set (via `StaticCredentialsProvider`)
2. **`OSS_ACCESS_KEY_ID` + `OSS_ACCESS_KEY_SECRET`** — standard OSS SDK credentials, used as fallback (via SDK's `EnvironmentVariableCredentialsProvider`)
3. If neither pair is set, the script exits with an error.

## `.env` Configuration Examples

### Option A: Dedicated OSS credentials

```bash
# DashScope API key (required for all skills)
DASHSCOPE_API_KEY=sk-your-key-here

# Custom OSS storage
QWEN_TMP_OSS_BUCKET=do-not-use-this-name-my-ai-assets
QWEN_TMP_OSS_REGION=ap-southeast-1
QWEN_TMP_OSS_AK_ID=Lxxxxxxxxxxxxxxx
QWEN_TMP_OSS_AK_SECRET=xxxxxxxxxxxxxxxx
```

### Option B: Reuse standard OSS SDK credentials

```bash
# DashScope API key
DASHSCOPE_API_KEY=sk-your-key-here

# Custom OSS storage (AK from standard OSS SDK env vars)
QWEN_TMP_OSS_BUCKET=do-not-use-this-name-my-ai-assets
QWEN_TMP_OSS_REGION=ap-southeast-1

# Standard OSS SDK credentials (shared with other OSS SDK consumers)
OSS_ACCESS_KEY_ID=Lxxxxxxxxxxxxxxx
OSS_ACCESS_KEY_SECRET=xxxxxxxxxxxxxxxx
```

## How It Works

When `QWEN_TMP_OSS_BUCKET` is set, all `resolve_file()` and `upload_file()` calls automatically route to your OSS bucket instead of DashScope temp storage. The upload returns a presigned `https://` URL that DashScope APIs accept natively — no special headers needed.

Files are stored under `{prefix}/{date}/{uuid}_{filename}` and remain in your bucket until you delete them. The presigned URL expires after the configured duration (default 24 hours), but the file itself persists.

**Note on vision skills**: The `--upload-files` flag is still required for vision scripts (analyze, reason, ocr) to trigger file upload. Without it, local files are base64-encoded regardless of custom OSS configuration. Image and video skills always upload local files automatically.

## Comparison

| | Default (DashScope Temp) | Custom OSS |
|---|---|---|
| URL format | `oss://` | `https://` (presigned) |
| File TTL | 48 hours (auto-deleted) | Permanent (user-managed) |
| Upload rate limit | 100 QPS (not expandable) | OSS limits (much higher) |
| Dependency | None (stdlib only) | `alibabacloud-oss-v2` |
| Setup | Zero config | Bucket + env vars |
| Production ready | No | Yes |

## Security

OSS credentials (`QWEN_TMP_OSS_AK_ID`, `QWEN_TMP_OSS_AK_SECRET`) must be treated with the same security level as `DASHSCOPE_API_KEY`:

- **Never hardcode** AccessKey credentials in source code.
- **Never log or display** `QWEN_TMP_OSS_AK_ID` or `QWEN_TMP_OSS_AK_SECRET` in plaintext. Use masked output (e.g. `Lxxx...xxxx`) in any diagnostic or error message.
- **Presigned URLs contain embedded credentials** (OSSAccessKeyId, Signature). Never log or display the full presigned URL including query parameters. Strip or mask the query string before any output.
- Add `.env` to `.gitignore` to prevent accidental commits.
- Use RAM users with minimal permissions (`oss:PutObject`, `oss:GetObject` on your bucket).
- Consider using internal endpoints (`QWEN_TMP_OSS_ENDPOINT`) when running in the same region/VPC as your OSS bucket to avoid public network charges.
