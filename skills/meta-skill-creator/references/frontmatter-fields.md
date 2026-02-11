# YAML Frontmatter Fields Reference

All supported fields for the `---` block in SKILL.md.

## Fields

| Field | Required | Type | Constraints | Description |
|-------|----------|------|-------------|-------------|
| `name` | No* | string | lowercase + hyphens, max 64 chars | Becomes the `/slash-command`. *Defaults to directory name if omitted. |
| `description` | Recommended | string | max 200 chars | What the skill does + when to use it. Claude uses this for auto-activation. |
| `argument-hint` | No | string | | Shown in autocomplete, e.g. `[issue-number]` or `[filename] [format]` |
| `disable-model-invocation` | No | bool | default: false | `true` = only user can invoke via `/name` |
| `user-invocable` | No | bool | default: true | `false` = hidden from user, only Claude can auto-load |
| `allowed-tools` | No | string | comma-separated | Tools Claude can use without asking permission |
| `model` | No | string | | Force a specific model for this skill |
| `context` | No | string | `fork` | `fork` = run in isolated subagent context |
| `agent` | No | string | `Explore`, `Plan`, `general-purpose` | Subagent type when `context: fork` |
| `hooks` | No | object | | Lifecycle hooks for the skill |

## Decision Guide

### When to set `disable-model-invocation: true`

Set this when the skill has **side effects** — it changes something:
- Creates or deletes files
- Deploys code
- Sends messages or emails
- Makes git commits
- Runs destructive commands
- Publishes content

### When to set `user-invocable: false`

Set this when the skill provides **background knowledge** that Claude should load automatically:
- Coding conventions and style guides
- API reference docs
- Project-specific patterns
- Domain knowledge

### When to set `context: fork`

Set this when the skill should run in **isolation**:
- Long-running research that shouldn't pollute conversation
- Tasks that need a clean context
- Parallel execution alongside other work

### When to set `allowed-tools`

Always set this. Principle of least privilege:
- Read-only skills: `Read, Grep, Glob`
- File-creating skills: `Bash, Read, Write, Glob, Grep`
- Interactive skills: add `AskUserQuestion`
- Research skills: add `WebSearch, WebFetch`

## Description Writing Guide

The description is the most important field. Claude reads ALL descriptions to decide which skill to activate.

**Formula**: `[What it does] + [When to use it]`

**Good examples**:
- `Create new Claude Code skills following best practices. Use when scaffolding a new skill.`
- `Run the full test suite and report failures. Use after code changes or before commits.`
- `Research a topic across Reddit, X, and web. Use when the user wants current discussions.`

**Bad examples**:
- `A helpful skill for coding` (too vague — when?)
- `Manages deployments and infrastructure and testing and monitoring` (too broad — split into multiple skills)
- `Use this skill to create things` (what things? when?)
