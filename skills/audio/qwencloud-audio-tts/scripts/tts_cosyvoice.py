#!/usr/bin/env python3
"""Synthesize speech from text via CosyVoice models (WebSocket API).

CosyVoice models require the DashScope SDK (WebSocket-based, not HTTP REST).
Run with --help for usage.

Dependencies:
    pip install dashscope>=1.24.6

Or with venv:
    python3 -m venv .venv && source .venv/bin/activate && pip install dashscope>=1.24.6
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 9):
    print(f"Error: Python 3.9+ required (found {sys.version}).", file=sys.stderr)
    sys.exit(1)

# Check dashscope dependency before other imports
try:
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer
except ImportError:
    print(
        "Error: dashscope SDK not installed.\n\n"
        "Install with:\n"
        "  pip install dashscope>=1.24.6\n\n"
        "Or use venv:\n"
        "  python3 -m venv .venv\n"
        "  source .venv/bin/activate  # Windows: .venv\\Scripts\\activate\n"
        "  pip install dashscope>=1.24.6",
        file=sys.stderr,
    )
    sys.exit(1)

import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwencloud_lib import require_api_key, run_update_signal  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEBSOCKET_URL = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference"
DEFAULT_MODEL = "cosyvoice-v3-flash"
DEFAULT_VOICE = "longanyang"

VOICES = {
    "longanyang": "Sunny young man (male)",
    "longanhuan": "Energetic cheerful female",
    "longhuhu_v3": "Innocent lively girl",
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_update_signal(caller=__file__)

    parser = argparse.ArgumentParser(
        description="CosyVoice TTS via DashScope SDK (WebSocket)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
models:
  cosyvoice-v3-flash   (default) High quality, fast
  cosyvoice-v3-plus    Highest quality, professional scenarios

voices (cosyvoice-v3-flash/plus):
  longanyang           (default) Sunny young man
  longanhuan           Energetic cheerful female
  longhuhu_v3          Innocent lively girl

examples:
  # Basic synthesis
  python {Path(__file__).name} --text "Hello, world!"

  # Chinese with specific voice
  python {Path(__file__).name} --text "你好世界" --voice longanhuan

  # High quality model
  python {Path(__file__).name} --text "Hello" --model cosyvoice-v3-plus

  # Save to specific file
  python {Path(__file__).name} --text "Hello" --output hello.mp3
""",
    )
    parser.add_argument("--text", "-t", required=True, help="Text to synthesize")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    parser.add_argument("--voice", "-v", default=DEFAULT_VOICE, help=f"Voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--output", "-o", type=Path, default=Path("output/qwencloud-audio-tts/cosyvoice.mp3"), help="Output file (default: output/qwencloud-audio-tts/cosyvoice.mp3)")
    parser.add_argument("--format", "-f", default="mp3", choices=["mp3", "wav", "pcm"], help="Audio format (default: mp3)")
    args = parser.parse_args()

    # Setup
    api_key = require_api_key(script_file=__file__, domain="CosyVoice TTS")
    dashscope.api_key = api_key
    dashscope.base_websocket_api_url = WEBSOCKET_URL

    # Synthesize
    print(f"Synthesizing: model={args.model}, voice={args.voice}", file=sys.stderr)
    try:
        synthesizer = SpeechSynthesizer(model=args.model, voice=args.voice)
        audio_data = synthesizer.call(args.text)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not audio_data:
        print("Error: No audio data returned.", file=sys.stderr)
        sys.exit(1)

    # Save
    output = args.output
    if output.suffix.lower() not in {".mp3", ".wav", ".pcm"}:
        output = output.with_suffix(f".{args.format}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio_data)

    print(f"Audio saved to {output}", file=sys.stderr)
    print(json.dumps({"audio_file": str(output), "size_bytes": len(audio_data)}))


if __name__ == "__main__":
    main()
