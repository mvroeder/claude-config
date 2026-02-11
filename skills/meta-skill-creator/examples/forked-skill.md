# Example: Forked Skill (Isolated Subagent)

A skill that runs in an isolated context without conversation history.

## Structure

```
~/.claude/skills/deep-review/
├── SKILL.md
└── IMPROVEMENTS.md
```

## SKILL.md

```yaml
---
name: deep-review
description: Deep code review of current PR changes. Use when reviewing pull requests or before merging.
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash
---
```

```markdown
Review the current PR changes thoroughly.

## Gather context

1. Get the diff: `gh pr diff`
2. Get changed files: `gh pr diff --name-only`
3. Read each changed file in full (not just the diff)

## Review criteria

For each changed file, check:
- **Correctness**: Logic errors, edge cases, off-by-one errors
- **Security**: Input validation, injection risks, secrets exposure
- **Performance**: N+1 queries, unnecessary allocations, missing indexes
- **Readability**: Naming, complexity, missing comments for non-obvious logic
- **Tests**: Are changes covered? Are tests meaningful?

## Report

Summarize findings as:
- 🔴 Must fix (blockers)
- 🟡 Should fix (improvements)
- 🟢 Looks good (positive callouts)

Include file paths and line numbers for each finding.

## Self-Improvement Protocol
When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for deep-review"
```

## Why this works

- `context: fork` — review runs in isolation, doesn't clutter the conversation
- `agent: Explore` — optimized for reading and searching code
- No `disable-model-invocation` — Claude can auto-trigger when PR context detected
- Dynamic context via `gh pr diff` command
- Structured output format (🔴🟡🟢) for easy scanning
