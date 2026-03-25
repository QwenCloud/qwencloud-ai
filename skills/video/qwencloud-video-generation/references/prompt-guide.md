# Video Generation — Prompt Guide

Techniques for building effective video prompts per mode. If the user provides specific prompt text, use it as-is — suggest enhancements only.

## Prompt Formula by Mode

| Mode | Formula | Focus |
|------|---------|-------|
| **t2v** | Entity + Scene + Motion + Aesthetic + Stylization | Full description |
| **i2v** | Motion + Camera Movement (+ Sound) | Movement only — image defines entity/scene/style |
| **kf2v** | Brief transition description (optional) | Images define start/end |
| **r2v** | `character1`/`character2` + Action + Lines + Scene | Character identifiers required |
| **vace** | Edit instruction for the function | Function-dependent |

## t2v / i2v Prompt Enhancement

Enrich short prompts by addressing each dimension:

| Dimension | Keywords / Patterns |
|-----------|-------------------|
| **Lighting** | `daylight`, `firelight`, `overcast`, `backlight`, `rim light`, `neon` |
| **Shot size** | `close-up`, `medium close-up`, `wide-angle`, `extreme full shot` |
| **Camera angle** | `eye level`, `high-angle`, `low-angle`, `over-the-shoulder`, `aerial` |
| **Composition** | `center`, `left-heavy`, `right-heavy`, `symmetrical`, `balanced` |
| **Lens** | `long-focus`, `ultra-wide-angle fisheye`, `medium-focus` |
| **Tone** | `warm tones`, `cool tones`, `low saturation`, `high contrast` |
| **Time** | `daytime`, `night`, `dawn`, `dusk`, `sunset` |
| **Camera move** | `camera pushes in`, `camera pulls out`, `camera moves left`, `fixed camera`, `orbiting` |

## i2v Prompt Specifics

Since the image already defines entity, scene, and style, focus on:

1. **Motion**: Specify what moves and how — `slowly raises her right hand` not just `moves`
2. **Camera**: Explicit direction and speed — `camera slowly pushes in`
3. **Static hold**: If camera should not move — `fixed camera, no camera movement`
4. **Speed modifiers**: `slowly`, `quickly`, `gently`, `violently`, `gradually`

## Multi-shot Structure

Required: `shot_type: "multi"` **AND** `prompt_extend: true`.

```
[Overall description — theme, mood, narrative style]
Shot 1 [0–Xs] [Shot type, camera, lighting. Action. Dialogue. Sound.]
Shot 2 [X–Ys] [Transition. New shot type. Camera move. Action.]
Shot 3 [Y–Zs] [Scene change. Resolution. Sound.]
```

## Sound Description (wan2.5/2.6 with audio)

Add sound to prompts for models that support audio generation:

| Category | Pattern |
|----------|---------|
| **Voice** | `[Character] says "[line]" in a [emotion] tone, [speed], [timbre]` |
| **SFX** | `[Source] [action], producing a [onomatopoeia] sound in [environment]` |
| **BGM** | `[Music style] background music, [mood]` |

## r2v Prompt Pattern

Use `character1`, `character2`, etc. matching `reference_urls` order:

```
[Scene setting]. character1 [action with posture/expression].
character2 [action/interaction]. character1 says "[line]".
[Camera movement]. [Sound description].
```

## Visual Style Keywords

| Style | Keywords |
|-------|----------|
| Felt | `felt style`, `small felt gnomes` |
| 3D cartoon | `3D cartoon style` |
| Pixel | `pixel style`, `pixel character` |
| Stop-motion | `puppet animation`, `claymation style` |
| Special FX | `tilt-shift photography`, `time-lapse photography` |

## Default negative_prompt

```
low quality, blurry, distorted, watermark, static, frozen, jittery,
inconsistent lighting, flickering
```

## prompt_extend Decision

| Condition | Value |
|-----------|:-----:|
| Short prompt (< 30 words) | `true` |
| Detailed prompt (advanced formula) | `false` |
| Multi-shot (`shot_type: "multi"`) | `true` (**required**) |
| Precise timing/composition control | `false` |
| Exploratory / creative | `true` |
