# Image Generation — Prompt Guide

Techniques for building high-quality image prompts. If the user provides specific prompt text, use it as-is — suggest enhancements only.

## Prompt Formulas

**Basic** (short descriptions, exploratory):

```
Entity + Environment + Style
```

**Advanced** (precise control):

```
Entity (description) + Environment (description) + Style (definition)
+ Camera Language + Atmosphere + Detail Modifiers
```

Example — user says "a cat on a windowsill":

```
A fluffy orange tabby cat with emerald eyes, lying on an aged wooden windowsill,
warm golden afternoon sunlight through sheer curtains, potted herbs beside it,
blurred garden visible through the window. Realistic photography, medium close-up,
eye-level, 85mm lens, warm tones, cozy atmosphere, soft bokeh, 8K, sharp focus.
```

## Style Keywords

| Category | Keywords |
|----------|----------|
| Realistic | `realistic, hyper realistic, commercial photography, 8K, sharp focus` |
| Artistic | `watercolor, oil painting, ink painting, pointillism, impressionist` |
| 3D / Render | `3D cartoon style, C4D rendering, Pixar style, clay style, felt style` |
| Asian | `Chinese ink style, Gongbi painting, ukiyo-e` |

## Camera Language

| Dimension | Keywords |
|-----------|----------|
| Shot size | `extreme close-up`, `close-up`, `medium shot`, `long shot` |
| Perspective | `eye level`, `bird's eye`, `low angle`, `aerial` |
| Lens | `macro`, `ultra-wide angle`, `telephoto`, `fisheye`, `85mm portrait` |

## Lighting

| Type | Keywords |
|------|----------|
| Natural | `sunlight`, `moonlight`, `morning sunlight`, `golden hour` |
| Dramatic | `backlight`, `rim light`, `side light`, `hard light` |
| Artificial | `neon lights`, `ambient lights`, `studio lighting`, `cinematic lighting` |

## Quality Modifiers

```
8K, UHD, masterpiece, best quality, sharp focus, professional color grading,
studio lighting, cinematic, award-winning photography
```

## Default negative_prompt

When user does not specify, consider:

```
low quality, blurry, distorted, deformed, bad anatomy, extra limbs,
watermark, text, signature, out of frame, cropped
```

## prompt_extend Decision

| Condition | Value |
|-----------|:-----:|
| Prompt < 30 words | `true` |
| Detailed prompt (advanced formula) | `false` |
| User wants precise control | `false` |
| Exploratory / creative | `true` |
| Iterating with fixed seed | `false` |
