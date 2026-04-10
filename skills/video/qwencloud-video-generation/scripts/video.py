#!/usr/bin/env python3
"""Video generation via Wan models on DashScope API.

Supports ALL video generation modes:
  t2v   -- text-to-video (prompt only)
  i2v   -- image-to-video based on first frame
  kf2v  -- image-to-video based on first + last frames
  r2v   -- reference-based video (character role-play)
  vace  -- video editing (multi-image ref, repainting, edit, extension, outpainting)

Submits async task, polls until completion, downloads video.
Self-contained, stdlib only.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwencloud_lib import (  # noqa: E402
    download_file,
    http_request,
    load_request,
    native_base_url,
    poll_task,
    require_api_key,
    run_update_signal,
)
from video_lib import (  # noqa: E402
    DEFAULT_MODELS,
    ENDPOINTS,
    MODE_I2V,
    MODE_KF2V,
    PAYLOAD_BUILDERS,
    RESOLVE_KEYS,
    _WAN27_I2V_MODELS,
    detect_mode,
    resolve_request_urls,
    extract_video_url,
    estimate_cost,
    resolve_resolution,
    format_task_status,
)

# ---------------------------------------------------------------------------
def _handle_result(result: dict[str, Any], args: argparse.Namespace) -> None:
    output = result.get("output", {})
    status = output.get("task_status", "")
    if status != "SUCCEEDED":
        msg = output.get("message", "Unknown error")
        print(f"Error: Task failed ({status}): {msg}", file=sys.stderr)
        sys.exit(1)

    video_url = extract_video_url(result)
    if not video_url:
        print(f"Error: No video URL in result: {result}", file=sys.stderr)
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    resp_file = args.output / "response.json"
    resp_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Response saved to {resp_file}", file=sys.stderr)

    video_file = args.output / "video.mp4"
    try:
        download_file(video_url, video_file)
    except Exception as e:
        print(f"Warning: Could not download video: {e}", file=sys.stderr)
    else:
        print(f"Video saved to {video_file}", file=sys.stderr)

    if args.print_response:
        print(json.dumps({
            "video_url": video_url,
            "local_path": str(video_file),
        }, ensure_ascii=False))

    print(f"Video URL: {video_url}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_update_signal(caller=__file__)
    parser = argparse.ArgumentParser(
        description="Generate video via Wan models (t2v/i2v/kf2v/r2v/vace)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
mode auto-detection (from request JSON fields):
  t2v   prompt only → text-to-video (default: wan2.6-t2v, or wan2.7-t2v)
  i2v   img_url/media/first_frame_url → image-to-video (default: wan2.6-i2v-flash, or wan2.7-i2v)
  kf2v  first_frame_url (without media) → keyframe-to-video (default: wan2.2-kf2v-flash)
  r2v   reference_urls → reference role-play (default: wan2.6-r2v-flash)
  vace  function → video editing/repaint/extend (default: wan2.1-vace-plus)

model version differences (handled automatically):
  wan2.6-t2v: uses "size" param (e.g. "1280*720"), supports seed, shot_type
  wan2.7-t2v: uses "resolution" + "ratio" params, auto-dubbing, 5000 char prompt
  wan2.6-i2v: single img_url input
  wan2.7-i2v: media array (first_frame, last_frame, driving_audio, first_clip)

request JSON fields (--request / --file):
  prompt            Text description (required for t2v/i2v/r2v, optional for vace)
  duration          Video length in seconds (default: 5, wan2.7: 2-15)
  size              Resolution for wan2.6 t2v/r2v, e.g. "1280*720"
  resolution        Resolution for wan2.7/i2v/kf2v, e.g. "720P", "1080P"
  ratio             Aspect ratio for wan2.7-t2v, e.g. "16:9", "9:16"
  img_url           First-frame image (i2v wan2.6)
  first_frame_url   First frame (wan2.7-i2v/kf2v)
  last_frame_url    Last frame (wan2.7-i2v/kf2v)
  first_clip_url    Video to continue (wan2.7-i2v)
  driving_audio_url Audio for lip-sync (wan2.7-i2v)
  media             Array of {type, url} for wan2.7-i2v
  reference_urls    Character reference URLs (r2v)
  function          VACE: repainting, editing, extension, outpainting
  video_url         Source video (VACE)
  audio_url         Audio track (t2v/i2v)
  negative_prompt   What to avoid
  seed              Reproducibility (wan2.6 only)
  prompt_extend     Auto-enhance prompt (default: true)
  watermark         Add watermark (default: false)

local files:
  Local paths are auto-uploaded to DashScope temp storage (48h TTL).

environment variables:
  DASHSCOPE_API_KEY  (required) API key — also loaded from .env
  QWEN_API_KEY       (alternative)
  QWEN_REGION        ap-southeast-1 (default)

examples:
  # Text-to-video (wan2.6)
  python scripts/video.py --request '{"prompt":"A cat playing piano","duration":5}'

  # Text-to-video with wan2.7 (ratio, auto-dubbing)
  python scripts/video.py --request '{"prompt":"Multi-shot cinematic...",
    "resolution":"1080P","ratio":"16:9","duration":15}' --model wan2.7-t2v

  # Image-to-video (wan2.6)
  python scripts/video.py --request '{"prompt":"Animate this","img_url":"photo.jpg"}'

  # Image-to-video with wan2.7 (first frame + audio sync)
  python scripts/video.py --request '{"prompt":"A rapper sings","first_frame_url":"rapper.png",
    "driving_audio_url":"rap.mp3"}' --model wan2.7-i2v

  # Video continuation with wan2.7
  python scripts/video.py --request '{"prompt":"Dog continues skateboarding",
    "first_clip_url":"dog_skateboard.mp4"}' --model wan2.7-i2v

  # Submit only, then resume later
  python scripts/video.py --request '{"prompt":"A sunset"}' --submit-only
  python scripts/video.py --task-id <TASK_ID>

  # VACE video editing
  python scripts/video.py --request '{"function":"repainting",
    "video_url":"input.mp4","prompt":"Change sky to sunset"}'
""",
    )
    parser.add_argument("--request", type=str, help="Inline JSON: fields depend on mode")
    parser.add_argument("--file", type=Path, help="Path to JSON file containing request body")
    parser.add_argument("--output", type=Path, default=Path("output/qwencloud-video-generation"),
                        help="Directory to save response and video (default: %(default)s)")
    parser.add_argument("--print-response", action="store_true", help="Print video URL to stdout")
    parser.add_argument("--model", type=str,
                        help="Model ID (overrides auto-default; see epilog for defaults per mode)")
    parser.add_argument("--mode", type=str, choices=["t2v", "i2v", "kf2v", "r2v", "vace"],
                        help="Force mode (auto-detected from request fields if omitted)")
    parser.add_argument("--poll-interval", type=int, default=15,
                        help="Seconds between poll attempts (default: 15)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Max seconds to wait for task (default: 600)")
    parser.add_argument("--submit-only", action="store_true",
                        help="Submit task, print task_id to stdout, exit without polling")
    parser.add_argument("--task-id", type=str,
                        help="Resume polling an existing task (skip submission)")
    parser.add_argument("--poll-once", action="store_true",
                        help="With --task-id: single status check, exit code 2 if not done")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress progress output during polling")
    args = parser.parse_args()

    verbose = not args.quiet
    api_key = require_api_key(script_file=__file__, domain="Video")

    # --- Single check mode ---
    if args.task_id and args.poll_once:
        result = http_request("GET", f"{native_base_url()}/tasks/{args.task_id}", api_key)
        if verbose:
            print(f"  {format_task_status(result)}", file=sys.stderr)
        status = result.get("output", {}).get("task_status", "")
        if status in ("SUCCEEDED", "FAILED", "CANCELED"):
            _handle_result(result, args)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(2)
        return

    # --- Resume mode ---
    if args.task_id:
        task_id = args.task_id
        if verbose:
            print(f"Resuming task: {task_id}", file=sys.stderr)
            print(f"Polling every {args.poll_interval}s (timeout: {args.timeout}s)...",
                  file=sys.stderr)
        try:
            result = poll_task(task_id, api_key,
                               timeout_s=args.timeout, interval=args.poll_interval,
                               verbose=verbose)
        except TimeoutError as e:
            print(f"Error: {e}", file=sys.stderr)
            print(f"Task may still be running. Resume with: --task-id {task_id}", file=sys.stderr)
            sys.exit(1)
        _handle_result(result, args)
        return

    # --- Normal mode: submit new task ---
    try:
        request = load_request(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    mode = args.mode or detect_mode(request)
    model = args.model or request.get("model") or DEFAULT_MODELS[mode]
    # Model-aware correction: wan2.7-i2v uses first_frame_url but needs i2v endpoint
    if model in _WAN27_I2V_MODELS and mode == MODE_KF2V:
        mode = MODE_I2V
    duration = request.get("duration", 5)
    resolution = resolve_resolution(request, mode)
    cost_str = estimate_cost(model, duration, resolution)

    if verbose:
        info = f"Mode: {mode} | Model: {model}"
        if cost_str:
            info += f" | Cost: {cost_str}"
        print(info, file=sys.stderr)

    resolve_request_urls(request, api_key, model, RESOLVE_KEYS[mode])

    builder = PAYLOAD_BUILDERS[mode]
    payload = builder(request, model)

    url = f"{native_base_url()}{ENDPOINTS[mode]}"

    try:
        resp = http_request("POST", url, api_key, payload,
                            extra_headers={"X-DashScope-Async": "enable"}, timeout=60)
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)

    task_id = resp.get("output", {}).get("task_id")
    if not task_id:
        print(f"Error: No task_id in response: {json.dumps(resp, ensure_ascii=False)[:500]}",
              file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"Task submitted: {task_id}", file=sys.stderr)

    if args.submit_only:
        print(task_id)
        return

    if verbose:
        print(f"Polling every {args.poll_interval}s (timeout: {args.timeout}s)...",
              file=sys.stderr)

    try:
        result = poll_task(task_id, api_key,
                           timeout_s=args.timeout, interval=args.poll_interval,
                           verbose=verbose)
    except TimeoutError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"Task may still be running. Resume with: --task-id {task_id}", file=sys.stderr)
        sys.exit(1)

    _handle_result(result, args)

if __name__ == "__main__":
    main()