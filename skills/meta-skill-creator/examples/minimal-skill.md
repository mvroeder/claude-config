# Example: Minimal Skill

The simplest possible skill — just a SKILL.md and IMPROVEMENTS.md, nothing else.

## Structure

```
~/.claude/skills/explain-code/
├── SKILL.md
└── IMPROVEMENTS.md
```

## SKILL.md

```yaml
---
name: explain-code
description: Explain code with analogies and ASCII diagrams. Use when the user asks how code works or wants to understand a codebase.
allowed-tools: Read, Grep, Glob
---
```

```markdown
When explaining code, follow this structure:

1. **Analogy first**: Compare the code to something from everyday life
2. **Draw a diagram**: Use ASCII art to show data/control flow
3. **Walk through step-by-step**: Explain each significant block
4. **Highlight one gotcha**: A common mistake or misconception

Keep explanations conversational. Adjust depth to the user's expertise level.

## Self-Improvement Protocol
When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for explain-code"
```

## Why this works

- Description says WHAT (explain code) and WHEN (user asks how code works)
- No `disable-model-invocation` → Claude can auto-activate
- `allowed-tools` is read-only (this skill doesn't create anything)
- Body is imperative and under 30 lines
- No supporting files needed — the instructions are simple enough
