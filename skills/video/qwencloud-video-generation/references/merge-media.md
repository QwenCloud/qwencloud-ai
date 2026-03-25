# Local Media Merging Guide

When generated video segments need to be **concatenated**, **audio added**, or **trimmed**, write and run a short script or CLI command. Choose the best tool based on the user's environment.

## When to Merge

| Scenario | Operation |
|----------|-----------|
| Stitch kf2v + vace extension segments into one video | concat |
| Add BGM or narration to silent kf2v/vace output | add audio |
| Concat multiple segments AND add audio in one step | concat + audio overlay |
| Trim a video to ≤3s for vace `video_extension` input | trim |

**When NOT to merge — let the model handle it:**

- Style transfer, outpainting, masking, object removal → use **vace** mode
- Multi-shot narrative with consistent characters → use **r2v** or **multi-shot t2v/i2v**
- Any editing that requires visual understanding of the content

## Tool Selection

Check the user's environment and pick the simplest available tool:

1. **System ffmpeg** (preferred — zero pip install, fastest):
   ```bash
   ffmpeg -version
   ```
   If available → use ffmpeg CLI commands below.

2. **moviepy 2.2.1** (fallback — bundles its own ffmpeg via imageio-ffmpeg):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate && pip install "moviepy==2.2.1"
   ```
   Always install in a **venv** to avoid polluting the system Python. Use when system ffmpeg is unavailable or the user prefers Python.

3. **Neither available** → help install one:
   - ffmpeg: `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux) / `winget install ffmpeg` (Windows)
   - moviepy: see venv setup below

## ffmpeg CLI Recipes

### Concat

Create a file list, then concatenate:

```bash
# file_list.txt (one file per line):
# file 'segment1.mp4'
# file 'segment2.mp4'
# file 'segment3.mp4'

ffmpeg -f concat -safe 0 -i file_list.txt -c copy output.mp4
```

If clips have different codecs or resolutions, re-encode:

```bash
ffmpeg -f concat -safe 0 -i file_list.txt -c:v libx264 -c:a aac output.mp4
```

### Add Audio

```bash
# Replace audio track (copy video, encode audio as aac)
ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest output.mp4
```

To loop short audio over a longer video:

```bash
ffmpeg -i video.mp4 -stream_loop -1 -i audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest output.mp4
```

### Trim

```bash
# Extract 2.0s to 5.0s (stream copy, fast)
ffmpeg -i video.mp4 -ss 2.0 -to 5.0 -c copy output.mp4
```

## moviepy Setup (venv)

**Version: moviepy 2.2.1** — pinned for reproducibility. This is the 2.x API; do NOT use moviepy 1.x patterns.

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate        # bash/zsh
pip install "moviepy==2.2.1"
python3 -c "import moviepy; print(f'moviepy {moviepy.__version__} OK')"
```

Platform-specific activation:

| Shell | Command |
|-------|---------|
| bash / zsh | `source .venv/bin/activate` |
| fish | `source .venv/bin/activate.fish` |
| Windows cmd | `.venv\Scripts\activate.bat` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |

### Cleanup

```bash
deactivate           # exit the venv
rm -rf .venv         # remove when no longer needed
```

The venv is local to the project directory and does not affect the system Python installation.

## moviepy 2.2.1 Recipes

**Import** — always use the 2.x import:

```python
from moviepy import *
```

### Forbidden Pattern

Do NOT use `AudioClip(make_frame_func, ...)` with numpy to synthesize audio programmatically — it crashes due to frame shape mismatches. Always load audio from existing files via `AudioFileClip`.

### Concat

```python
from moviepy import *

clips = [VideoFileClip(f) for f in ["seg1.mp4", "seg2.mp4"]]
result = concatenate_videoclips(clips, method="compose")
result.write_videofile("output.mp4", codec="libx264", audio_codec="aac")
for c in clips:
    c.close()
```

### Add Audio

```python
from moviepy import *

video = VideoFileClip("video.mp4")
audio = AudioFileClip("audio.mp3").with_duration(video.duration)
final = video.with_audio(audio)
final.write_videofile("output.mp4", codec="libx264", audio_codec="aac")
video.close()
```

### Mix Voiceover + BGM

```python
from moviepy import *

video = VideoFileClip("video.mp4")
voiceover = AudioFileClip("voiceover.wav").with_volume_scaled(1.0)
bgm = AudioFileClip("bgm.mp3").with_duration(video.duration).with_volume_scaled(0.3)
mixed = CompositeAudioClip([bgm, voiceover])
final = video.with_audio(mixed)
final.write_videofile("output.mp4", codec="libx264", audio_codec="aac")
video.close()
```

### Add Image/Poster as Clip

```python
from moviepy import *

poster = ImageClip("poster.png").with_duration(3)
video = VideoFileClip("video.mp4")
result = concatenate_videoclips([video, poster], method="compose")
result.write_videofile("output.mp4", codec="libx264", audio_codec="aac")
video.close()
```

### Trim

```python
from moviepy import *

clip = VideoFileClip("video.mp4")
trimmed = clip.subclipped(2.0, 5.0)
trimmed.write_videofile("output.mp4", codec="libx264", audio_codec="aac")
clip.close()
```

## Implementation Notes

- **Always specify `audio_codec="aac"`** (moviepy) or `-c:a aac` (ffmpeg) — omitting this can produce silent output when the bundled ffmpeg picks an incompatible default codec.
- **Audio looping**: When BGM is shorter than video, loop it. **Prefer ffmpeg**: `-stream_loop -1 ... -shortest`. With moviepy: `concatenate_audioclips([audio] * N)` where N covers the video duration.
- **Different resolutions**: For ffmpeg, re-encode with explicit resolution. For moviepy, use `method="compose"` in `concatenate_videoclips`.
- **Resource cleanup**: Always call `.close()` on moviepy clips after writing to avoid file handle leaks.
- **Output directory**: Create parent directories before writing (`mkdir -p` or `Path.mkdir(parents=True)`).
- **Default output path**: `output/qwencloud-video-generation/` under the current working directory.

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'moviepy.editor'` | moviepy 2.x changed import path | Use `from moviepy import *` (not `from moviepy.editor import *`) |
| `AttributeError: 'VideoFileClip' object has no attribute 'set_audio'` | moviepy 1.x API | Use `.with_audio()` (2.x API) |
| `AttributeError: ... has no attribute 'subclip'` | moviepy 1.x API | Use `.subclipped()` (2.x API) |
| Silent output video | Missing audio_codec | Add `audio_codec="aac"` to `write_videofile()` |
| `FileNotFoundError: ffmpeg` | ffmpeg not bundled | Install system ffmpeg or use moviepy in venv (includes imageio-ffmpeg) |
| Output file is 0 bytes | Write failed | Check disk space, permissions, and ensure output directory exists |
