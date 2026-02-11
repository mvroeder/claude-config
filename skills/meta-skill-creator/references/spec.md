# Claude Code Skill Specification

Complete reference for building skills. Claude reads this during skill creation.

## Directory Structure

```
~/.claude/skills/{skill-name}/
├── SKILL.md              # Required: YAML frontmatter + instructions
├── IMPROVEMENTS.md       # Required (our convention): self-evolution log
├── references/           # Optional: detailed docs Claude reads on demand
├── examples/             # Optional: example inputs/outputs
├── scripts/              # Optional: executable automation
└── assets/               # Optional: media files used in output
```

**Location hierarchy** (higher overrides lower):
1. Enterprise (Managed Settings)
2. Personal: `~/.claude/skills/<name>/SKILL.md`
3. Project: `.claude/skills/<name>/SKILL.md`
4. Plugin: `<plugin>/skills/<name>/SKILL.md`

## SKILL.md Anatomy

Two parts separated by `---` markers:

```yaml
---
# YAML Frontmatter (metadata)
name: skill-name
description: What it does and when to use it.
---

# Markdown Body (instructions Claude follows)
Step-by-step workflow...
```

## Progressive Disclosure (3 Levels)

| Level | What | When loaded | Budget |
|-------|------|-------------|--------|
| 1. Metadata | name + description | Always in context | ~100 words each, 2% of context window total |
| 2. Body | SKILL.md markdown | When skill triggers | < 500 lines |
| 3. Resources | references/, scripts/ | On demand via file reads | Unlimited |

**Key insight**: Only Level 1 costs context budget permanently. Levels 2-3 load dynamically.

## String Substitutions

Available in SKILL.md body:

| Variable | Expands to |
|----------|-----------|
| `$ARGUMENTS` | All arguments passed after skill name |
| `$ARGUMENTS[N]` or `$N` | Positional argument (0-based) |
| `${CLAUDE_SESSION_ID}` | Unique session identifier |

## Dynamic Context Injection

Preprocess commands before Claude sees content:

```markdown
Current PR diff: !`gh pr diff`
Changed files: !`gh pr diff --name-only`
```

The command output replaces the placeholder at invocation time.

## Invocation Control

| Setting | User can invoke | Claude can auto-invoke | When body loads |
|---------|----------------|----------------------|-----------------|
| (default) | Yes via `/name` | Yes if relevant | On invocation |
| `disable-model-invocation: true` | Yes via `/name` | No | On `/name` only |
| `user-invocable: false` | No (hidden) | Yes if relevant | When Claude decides |

**Rule of thumb**:
- Side effects (create files, deploy, commit, send) → `disable-model-invocation: true`
- Background knowledge (conventions, style guides) → `user-invocable: false`
- General purpose → default (both can invoke)

## Context Budget

- All skill descriptions share 2% of context window (~16,000 chars)
- Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var
- Warning appears if budget exceeded
- Solution: shorten descriptions or reduce skill count

## Body Writing Rules

1. **Imperative form**: "Extract the data", not "This skill extracts data"
2. **Under 500 lines**: Move details to references/
3. **Reference supporting files explicitly**: "For field details, read references/fields.md"
4. **No duplication**: Don't repeat reference content in body
5. **No "When to Use" in body**: That belongs in the description field only
6. **Extended thinking**: Include "ultrathink" in body to activate extended thinking

## Anti-Patterns

Do NOT include these files in a skill directory:
- `README.md` — skill is self-documenting via SKILL.md
- `INSTALLATION_GUIDE.md` — skills don't need installation
- `CHANGELOG.md` — use IMPROVEMENTS.md instead
- `QUICK_REFERENCE.md` — use references/ directory instead

Do NOT:
- Nest references more than one level deep
- Duplicate information between SKILL.md and reference files
- Put "When to Use" sections in the body
- Make descriptions vague ("A helpful skill") — be specific about what AND when

## Self-Evolution Pattern (IMPROVEMENTS.md)

Every skill includes an IMPROVEMENTS.md where Claude logs observations:

```markdown
## 2026-02-11
- **Context**: User asked for X but skill produced Y
- **Observation**: Missing handling for edge case Z
- **Suggested change**: Add step between 3 and 4 to check for Z
```

**Rules**:
- Claude writes to IMPROVEMENTS.md, never modifies SKILL.md directly
- Claude flags improvements to the user: "I logged a potential improvement for {skill}"
- User reviews and promotes changes when ready
