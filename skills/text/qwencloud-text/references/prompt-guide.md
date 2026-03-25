# Text Chat — Prompt Guide

Techniques for building effective system prompts and user prompts. If the user provides specific prompt text, use it as-is — suggest enhancements only.

## System Prompt: CO-STAR Framework

Construct system prompts by addressing each element:

| Element | Question | Example |
|---------|----------|---------|
| **C**ontext | What background does the model need? | `You are a senior backend engineer reviewing Java code.` |
| **O**bjective | What task should it complete? | `Identify security vulnerabilities and suggest fixes.` |
| **S**tyle | What writing style? | `Concise, technical, with code examples.` |
| **T**one | What tone? | `Professional and constructive.` |
| **A**udience | Who is the reader? | `Mid-level developers on the team.` |
| **R**esponse | What output format? | `Markdown with headers per vulnerability, severity rating, and fix snippet.` |

Template:

```
#Context#
You are [role]. Your expertise includes [domains].

#Objective#
[Primary task]. Specifically:
- [Sub-task 1]
- [Sub-task 2]

#Style#
[Style descriptor].

#Tone#
[Tone descriptor].

#Audience#
[Target group]. Adjust depth accordingly.

#Response#
Format: [format]. Always include: [required]. Never include: [prohibited].
```

## User Prompt Enhancement

| Technique | When to Apply | Pattern |
|-----------|--------------|---------|
| **Task steps** | Multi-step analysis | `#Task Steps#\n1. First…\n2. Then…\n3. Finally…` |
| **Separators** | Long input with sections | Wrap sections with `###` or `===` |
| **Few-shot** | Format-sensitive output | Include 1–2 input/output examples |
| **Chain of Thought** | Reasoning, math, logic | `Think step by step. Show reasoning before the answer.` |

## Feature-Specific Prompting

| Feature | Prompt Tip |
|---------|-----------|
| `enable_thinking: true` | Provide sufficient context; avoid trivially simple questions |
| `tools` (function calling) | In system prompt, clarify when each tool should be called and parameter constraints |
| `response_format` (JSON) | Describe each field's meaning and constraints in system prompt |
| `enable_search: true` | State recency requirements explicitly (e.g. "as of March 2026") |
