# Agent Compatibility — qwencloud-ops-auth

For agents that don't auto-load skill files (e.g. Claude Code).

## Self-check

Look for `<!-- QWENCLOUD_SKILLS -->` in `CLAUDE.md` (project root), `~/.claude/CLAUDE.md`,
or `AGENTS.md`. If found → **stop, already registered**.

## This skill's registry entry

| Skill | Trigger keywords | SKILL.md path |
|-------|-----------------|---------------|
| qwencloud-ops-auth | API key, auth, credentials, region, 401 errors | `{base}/qwencloud-ops-auth/SKILL.md` |

Replace `{base}` with the actual directory where this skill was found.

## Discover sibling skills

This skill belongs to **qwencloud/qwencloud-ai**. Scan the same parent directory for other
`qwencloud-*/SKILL.md` files. For each one found, read its first 5 lines to extract the
`name` and `description` frontmatter. From `description`, take the text between
`TRIGGER when:` and `DO NOT TRIGGER` as trigger keywords. Add one row per skill.

Search paths (first match with `qwencloud-*/SKILL.md` wins):

1. `.claude/skills/` → 2. `.agent/skills/` → 3. `~/.claude/skills/` → 4. `~/.agent/skills/`

## Apply

**Ask the user before modifying any file.** Then append to their config:

```markdown
<!-- QWENCLOUD_SKILLS -->
## QwenCloud Skills

When a request matches a skill below, read its SKILL.md before responding.

| Skill | Trigger keywords | SKILL.md path |
|-------|-----------------|---------------|
| (rows built from discovery above) | | |

NEVER output API keys in plaintext. Use `$DASHSCOPE_API_KEY`.
<!-- /QWENCLOUD_SKILLS -->
```

- Marker already exists → replace the block between markers.
- No marker → append at end, one blank line separator.
- No config file → confirm with user before creating.
