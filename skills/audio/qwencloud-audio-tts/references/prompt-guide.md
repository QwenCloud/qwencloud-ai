# Audio TTS — Prompt Guide

Techniques for optimizing TTS text input and voice instructions. If the user provides specific text or instructions, use them as-is — suggest enhancements only.

## Text Formatting for Natural Speech

TTS quality is highly sensitive to punctuation and structure:

| Technique | Effect | Example |
|-----------|--------|---------|
| Commas | Short pause | `Hello, welcome to our event.` |
| Periods | Full stop | `Thank you. Let's begin.` |
| Ellipsis | Dramatic pause | `And the winner is... Team Alpha!` |
| Exclamation | Energy / emphasis | `This is incredible!` |
| Question mark | Rising intonation | `Are you ready?` |
| Short sentences | Clearer delivery | Break 100+ word paragraphs into 1–2 sentence chunks |

For mixed-language text, set `language_type: "Auto"`.

## Instructions Templates (qwen3-tts-instruct-flash only)

| Scenario | Instructions |
|----------|-------------|
| News anchor | `Professional, authoritative tone. Clear enunciation, moderate pacing.` |
| Audiobook | `Warm, engaging narration. Varied pacing — slow for drama, faster for action.` |
| Children's story | `Cheerful, animated voice. Exaggerated intonation. Slow and playful.` |
| Product ad | `Confident enthusiasm. Dynamic pacing — measured start, building momentum. Emphasize product name.` |
| Meditation | `Very slow, soft, calm. Long pauses between sentences. Almost whispered.` |
| Tutorial | `Clear, patient, instructional. Moderate pace with brief pauses between steps.` |

General pattern:

```
Speak in a [emotion] tone with [speed] pacing. Use a [quality] voice,
as if [character/scenario]. [Additional: emphasis, pauses, accent].
```

## Voice Selection

| Scenario | Voice | Reason |
|----------|-------|--------|
| Business narration | Ethan, Aiden | Steady, professional male voice |
| Warm storytelling | Cherry, Serena | Soft, warm female voice |
| Energetic marketing | Chelsie | Upbeat, lively female voice |
| General purpose | Aria | Natural, versatile female voice |
