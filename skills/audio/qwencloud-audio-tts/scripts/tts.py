#!/usr/bin/env python3
"""Synthesize speech from text via Qwen TTS models on DashScope API.

Supports multiple voices, instruction-controlled style, and automatic audio
download. Self-contained, stdlib only.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 9):
    print(f"Error: Python 3.9+ required (found {sys.version}). "
          "Install: https://www.python.org/downloads/", file=sys.stderr)
    sys.exit(1)

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwencloud_lib import (  # noqa: E402
    download_file,
    http_request,
    load_request,
    native_base_url,
    require_api_key,
    run_update_signal,
)

# ---------------------------------------------------------------------------
# TTS constants
# ---------------------------------------------------------------------------

TTS_GENERATION_PATH = "/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen3-tts-flash"
DEFAULT_VOICE = "Cherry"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _guess_audio_ext(url: str, default: str = ".wav") -> str:
    """Extract audio extension from URL path, ignoring query params."""
    path = urlparse(url).path
    for ext in (".wav", ".mp3", ".flac", ".ogg", ".pcm", ".aac"):
        if path.endswith(ext):
            return ext
    return default


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_update_signal(caller=__file__)
    parser = argparse.ArgumentParser(
        description="Synthesize speech from text via Qwen TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
request JSON fields (--request / --file):
  text                (required) Text to synthesize into speech
  voice               Voice ID — overridden by --voice flag (default: Cherry)
  model               Model ID — overridden by --model flag
  language_type       Force language: "zh" / "en" / "ja" / "ko" etc.
  instructions        Style instructions for instruct models, e.g.
                      "Speak slowly with a warm, gentle tone"
  optimize_instructions  true/false — auto-optimize instruction text

models:
  qwen3-tts-flash                (default) Fast, multi-voice
  qwen3-tts-instruct-flash       Instruction-controlled style/emotion/pace

  Note: CosyVoice models (cosyvoice-v3-plus/flash) require WebSocket API.
        Use tts_cosyvoice.py instead of this script.

output:
  --output can be a directory (audio saved as audio.wav/mp3 inside)
  or a specific file path (e.g. output/speech.mp3). Extension is
  auto-detected from the API response URL.

environment variables:
  DASHSCOPE_API_KEY   (required) API key — also loaded from .env
  QWEN_API_KEY        (alternative) Alias for DASHSCOPE_API_KEY
  QWEN_REGION         ap-southeast-1 (default)

examples:
  # Simple TTS
  python scripts/tts.py --request '{"text":"Hello, world!"}'

  # Chinese text with specific voice
  python scripts/tts.py --request '{"text":"你好世界"}' --voice Chelsie

  # Instruction-controlled style
  python scripts/tts.py --request '{"text":"Breaking news today...",
    "instructions":"Speak in a serious news anchor tone, moderate pace"}' \\
    --model qwen3-tts-instruct-flash

  # Save to specific file
  python scripts/tts.py --request '{"text":"Hello"}' --output output/hello.mp3
""",
    )
    parser.add_argument("--request", type=str,
                        help="Inline JSON: must contain 'text' field")
    parser.add_argument("--file", type=Path,
                        help="Path to JSON file containing request body")
    parser.add_argument("--output", type=Path, default=Path("output/qwencloud-audio-tts"),
                        help="Output directory or file path (default: %(default)s)")
    parser.add_argument("--print-response", action="store_true",
                        help="Print audio URL and file path JSON to stdout")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help="Model ID (default: %(default)s). See epilog for model list")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE,
                        help="Voice ID (default: %(default)s)")
    args = parser.parse_args()

    try:
        request = load_request(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    text = request.get("text")
    if not text:
        print("Error: text is required.", file=sys.stderr)
        sys.exit(1)

    voice = request.get("voice") or args.voice
    model = request.get("model") or args.model

    input_obj: dict[str, Any] = {"text": text, "voice": voice}
    if request.get("language_type"):
        input_obj["language_type"] = request["language_type"]

    payload: dict[str, Any] = {"model": model, "input": input_obj}

    if request.get("instructions") and "instruct" in model.lower():
        input_obj["instructions"] = request["instructions"]
        if request.get("optimize_instructions") is not None:
            input_obj["optimize_instructions"] = request["optimize_instructions"]

    api_key = require_api_key(script_file=__file__, domain="TTS")
    url = f"{native_base_url()}{TTS_GENERATION_PATH}"

    try:
        resp = http_request("POST", url, api_key, payload, timeout=60)
    except RuntimeError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)

    audio_url = (resp.get("output") or {}).get("audio", {}).get("url")
    if not audio_url:
        print(f"Error: No audio URL in response: {resp}", file=sys.stderr)
        sys.exit(1)

    out = args.output
    _AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".pcm", ".aac"}

    if out.suffix.lower() in _AUDIO_EXTS:
        audio_file = out
        out_dir = out.parent
    else:
        out_dir = out
        ext = _guess_audio_ext(audio_url)
        audio_file = out_dir / f"audio{ext}"

    out_dir.mkdir(parents=True, exist_ok=True)

    resp_file = out_dir / "response.json"
    resp_file.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Response saved to {resp_file}", file=sys.stderr)

    try:
        download_file(audio_url, audio_file)
    except Exception as e:
        print(f"Warning: Could not download audio: {e}", file=sys.stderr)
        print(f"Audio URL (manual download): {audio_url}", file=sys.stderr)
    else:
        print(f"Audio saved to {audio_file}", file=sys.stderr)

    if args.print_response:
        print(json.dumps({"audio_url": audio_url, "audio_file": str(audio_file)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
