"""Video generation helpers: mode constants, payload builders, result extraction.

Shared library for video.py. Contains all mode constants, model defaults,
endpoint paths, payload construction, and result parsing/formatting logic.
Stdlib only -- no pip install required.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qwencloud_lib import resolve_file  # noqa: E402

# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------

MODE_T2V = "t2v"
MODE_I2V = "i2v"
MODE_KF2V = "kf2v"
MODE_R2V = "r2v"
MODE_VACE = "vace"

DEFAULT_MODELS: dict[str, str] = {
    MODE_T2V: "wan2.6-t2v",
    MODE_I2V: "wan2.6-i2v-flash",
    MODE_KF2V: "wan2.2-kf2v-flash",
    MODE_R2V: "wan2.6-r2v-flash",
    MODE_VACE: "wan2.1-vace-plus",
}

# wan2.7 models use the same modes but with different payload structure
_WAN27_T2V_MODELS = frozenset({"wan2.7-t2v"})
_WAN27_I2V_MODELS = frozenset({"wan2.7-i2v"})

ENDPOINTS: dict[str, str] = {
    MODE_T2V: "/services/aigc/video-generation/video-synthesis",
    MODE_I2V: "/services/aigc/video-generation/video-synthesis",
    MODE_KF2V: "/services/aigc/image2video/video-synthesis",
    MODE_R2V: "/services/aigc/video-generation/video-synthesis",
    MODE_VACE: "/services/aigc/video-generation/video-synthesis",
}

_PRICING_URL = "https://docs.qwencloud.com/developer-guides/getting-started/pricing"

# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

def detect_mode(request: dict[str, Any]) -> str:
    """Auto-detect video generation mode from request fields."""
    if request.get("function"):
        return MODE_VACE
    if request.get("reference_urls"):
        return MODE_R2V
    # wan2.7-i2v uses media array or first_clip_url
    if request.get("media") or request.get("first_clip_url"):
        return MODE_I2V
    if request.get("first_frame_url"):
        return MODE_KF2V
    if request.get("img_url") or request.get("reference_image"):
        return MODE_I2V
    return MODE_T2V

# ---------------------------------------------------------------------------
# File resolution helpers
# ---------------------------------------------------------------------------

RESOLVE_KEYS: dict[str, list[str]] = {
    MODE_T2V: ["audio_url"],
    MODE_I2V: ["img_url", "reference_image", "audio_url",
               "first_frame_url", "last_frame_url", "driving_audio_url", "first_clip_url"],
    MODE_KF2V: ["first_frame_url", "last_frame_url"],
    MODE_R2V: ["reference_urls"],
    MODE_VACE: ["video_url", "mask_image_url", "mask_video_url",
                "ref_images_url", "first_clip_url", "last_clip_url",
                "first_frame_url", "last_frame_url"],
}


def resolve_request_urls(request: dict[str, Any], api_key: str, model: str,
                         keys: list[str]) -> None:
    """In-place resolve local file paths to OSS URLs for the given request keys."""
    for key in keys:
        val = request.get(key)
        if val is None:
            continue
        if isinstance(val, str):
            request[key] = resolve_file(val, api_key=api_key, model=model)
        elif isinstance(val, list):
            request[key] = [resolve_file(str(v), api_key=api_key, model=model) for v in val]

# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def build_t2v_payload(request: dict[str, Any], model: str) -> dict[str, Any]:
    """Build payload for text-to-video generation (wan2.6/wan2.7)."""
    is_v27 = model in _WAN27_T2V_MODELS

    input_obj: dict[str, Any] = {"prompt": request.get("prompt", "")}
    if request.get("negative_prompt"):
        input_obj["negative_prompt"] = request["negative_prompt"]
    if request.get("audio_url"):
        input_obj["audio_url"] = request["audio_url"]

    params: dict[str, Any] = {"duration": request.get("duration", 5)}

    if is_v27:
        # wan2.7-t2v: uses resolution and ratio
        params["resolution"] = request.get("resolution", "1080P")
        if request.get("ratio"):
            params["ratio"] = request["ratio"]
    else:
        # wan2.6-t2v: uses size
        if request.get("size"):
            params["size"] = request["size"]
        for key in ("seed", "shot_type"):
            if request.get(key) is not None:
                params[key] = request[key]

    for key in ("prompt_extend", "watermark"):
        if request.get(key) is not None:
            params[key] = request[key]

    return {"model": model, "input": input_obj, "parameters": params}


def build_i2v_payload(request: dict[str, Any], model: str) -> dict[str, Any]:
    """Build payload for image-to-video generation (wan2.6/wan2.7)."""
    is_v27 = model in _WAN27_I2V_MODELS

    # wan2.7-i2v uses media array
    if is_v27 or request.get("media") or request.get("first_clip_url"):
        return _build_i2v_v27_payload(request, model)

    # wan2.6-i2v uses img_url
    img_url = request.get("img_url") or request.get("reference_image", "")
    input_obj: dict[str, Any] = {"prompt": request.get("prompt", ""), "img_url": img_url}
    if request.get("negative_prompt"):
        input_obj["negative_prompt"] = request["negative_prompt"]
    if request.get("audio_url"):
        input_obj["audio_url"] = request["audio_url"]

    params: dict[str, Any] = {
        "resolution": request.get("resolution", "720P"),
        "duration": request.get("duration", 5),
    }
    for key in ("prompt_extend", "watermark", "seed", "shot_type", "template", "audio"):
        if request.get(key) is not None:
            params[key] = request[key]

    return {"model": model, "input": input_obj, "parameters": params}


def _build_i2v_v27_payload(request: dict[str, Any], model: str) -> dict[str, Any]:
    """Build payload for wan2.7-i2v unified image-to-video generation.

    Supports: first_frame, last_frame, driving_audio, first_clip (video continuation).
    """
    media: list[dict[str, str]] = []

    if request.get("media"):
        media = request["media"]
    else:
        if request.get("first_frame_url"):
            media.append({"type": "first_frame", "url": request["first_frame_url"]})
        if request.get("last_frame_url"):
            media.append({"type": "last_frame", "url": request["last_frame_url"]})
        if request.get("driving_audio_url"):
            media.append({"type": "driving_audio", "url": request["driving_audio_url"]})
        if request.get("first_clip_url"):
            media.append({"type": "first_clip", "url": request["first_clip_url"]})

    if not media:
        raise ValueError(
            "wan2.7-i2v requires at least one media asset. "
            "Use first_frame_url, first_clip_url, or media array."
        )

    input_obj: dict[str, Any] = {"media": media}
    if request.get("prompt"):
        input_obj["prompt"] = request["prompt"]
    if request.get("negative_prompt"):
        input_obj["negative_prompt"] = request["negative_prompt"]

    params: dict[str, Any] = {
        "resolution": request.get("resolution", "1080P"),
        "duration": request.get("duration", 5),
    }
    for key in ("prompt_extend", "watermark"):
        if request.get(key) is not None:
            params[key] = request[key]

    return {"model": model, "input": input_obj, "parameters": params}


def build_kf2v_payload(request: dict[str, Any], model: str) -> dict[str, Any]:
    """Build payload for keyframe-to-video generation."""
    input_obj: dict[str, Any] = {
        "first_frame_url": request.get("first_frame_url", ""),
        "prompt": request.get("prompt", ""),
    }
    if request.get("last_frame_url"):
        input_obj["last_frame_url"] = request["last_frame_url"]
    if request.get("template"):
        input_obj["template"] = request["template"]

    params: dict[str, Any] = {
        "resolution": request.get("resolution", "720P"),
        "duration": 5,  # Fixed at 5 seconds per qwdocs
    }
    for key in ("prompt_extend", "watermark", "seed"):
        if request.get(key) is not None:
            params[key] = request[key]

    return {"model": model, "input": input_obj, "parameters": params}


def build_r2v_payload(request: dict[str, Any], model: str) -> dict[str, Any]:
    """Build payload for reference-based role-play video generation."""
    input_obj: dict[str, Any] = {
        "prompt": request.get("prompt", ""),
        "reference_urls": request.get("reference_urls", []),
    }
    params: dict[str, Any] = {
        "size": request.get("size", "1280*720"),
        "duration": request.get("duration", 5),
    }
    for key in ("shot_type", "watermark", "audio"):
        if request.get(key) is not None:
            params[key] = request[key]

    return {"model": model, "input": input_obj, "parameters": params}


def build_vace_payload(request: dict[str, Any], model: str) -> dict[str, Any]:
    """Build payload for VACE video editing (repainting, extension, outpainting, etc.)."""
    func = request["function"]
    input_obj: dict[str, Any] = {"function": func}

    if request.get("prompt"):
        input_obj["prompt"] = request["prompt"]

    url_fields = [
        "video_url", "mask_image_url", "mask_video_url",
        "first_clip_url", "last_clip_url",
        "first_frame_url", "last_frame_url",
    ]
    for field in url_fields:
        if request.get(field):
            input_obj[field] = request[field]

    if request.get("ref_images_url"):
        input_obj["ref_images_url"] = request["ref_images_url"]
    if request.get("mask_frame_id") is not None:
        input_obj["mask_frame_id"] = request["mask_frame_id"]

    params: dict[str, Any] = {}
    param_keys = [
        "prompt_extend", "size", "watermark", "obj_or_bg",
        "control_condition", "strength", "mask_type", "expand_ratio",
        "top_scale", "bottom_scale", "left_scale", "right_scale",
    ]
    for key in param_keys:
        if request.get(key) is not None:
            params[key] = request[key]

    return {"model": model, "input": input_obj, "parameters": params}


PAYLOAD_BUILDERS: dict[str, Any] = {
    MODE_T2V: build_t2v_payload,
    MODE_I2V: build_i2v_payload,
    MODE_KF2V: build_kf2v_payload,
    MODE_R2V: build_r2v_payload,
    MODE_VACE: build_vace_payload,
}

# ---------------------------------------------------------------------------
# Result extraction and status formatting
# ---------------------------------------------------------------------------

def extract_video_url(result: dict[str, Any]) -> str | None:
    """Extract video URL from task result, checking both output formats."""
    output = result.get("output", {})
    url = output.get("video_url")
    if url:
        return url
    results = output.get("results", [])
    if results and isinstance(results[0], dict):
        return results[0].get("url")
    return None


def estimate_cost(_model: str, _duration: int, _resolution: str,
                  _cny: bool = False) -> str:
    """Return a pricing page reference instead of a hardcoded estimate."""
    return f"see {_PRICING_URL} for current rates"


def resolve_resolution(request: dict[str, Any], mode: str) -> str:
    """Derive a human-readable resolution label from the request for cost estimation."""
    # Modes that use resolution parameter
    if mode in (MODE_I2V, MODE_KF2V):
        return request.get("resolution", "720P")
    # Modes that use size parameter (wan2.6 t2v, r2v)
    if mode in (MODE_T2V, MODE_R2V):
        # If resolution is explicitly set (wan2.7), use it
        if request.get("resolution"):
            return request["resolution"]
        size = request.get("size", "1280*720")
        try:
            width, height = size.split("*")
            pixels = int(width) * int(height)
        except (ValueError, AttributeError):
            return "720P"
        if pixels >= 1920 * 1080:
            return "1080P"
        if pixels >= 1280 * 720:
            return "720P"
        return "480P"
    return "720P"


def format_task_status(result: dict[str, Any], elapsed: int | None = None) -> str:
    """Format a human-readable task status line for progress reporting."""
    output = result.get("output", {})
    status = output.get("task_status", "UNKNOWN")
    task_id = output.get("task_id", "")
    parts = []
    if elapsed is not None:
        parts.append(f"[{elapsed}s]")
    parts.append(f"task={task_id}" if task_id else "")
    parts.append(f"status={status}")
    metrics = output.get("task_metrics", {})
    if metrics:
        total = metrics.get("TOTAL", 0)
        succeeded = metrics.get("SUCCEEDED", 0)
        failed = metrics.get("FAILED", 0)
        if total:
            parts.append(f"progress={succeeded}/{total}")
        if failed:
            parts.append(f"failed={failed}")
    msg = output.get("message", "")
    if msg and status in ("FAILED", "CANCELED"):
        parts.append(f"msg={msg[:120]}")
    if output.get("video_url"):
        parts.append("video_url=ready")
    return "  ".join(part for part in parts if part)
