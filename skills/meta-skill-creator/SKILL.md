---
name: meta-skill-creator
description: Create new Claude Code skills following best practices with proper structure, frontmatter, and self-evolution pattern. Use when scaffolding or building a new skill.
argument-hint: '[skill-name] [one-line description]'
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion
---

# Create a New Skill

Build a skill at `~/.claude/skills/$ARGUMENTS[0]` following the specification.

## Step 1: Parse Arguments

Extract from `$ARGUMENTS`:
- `SKILL_NAME` = first argument (the directory/command name)
- `DESCRIPTION` = remaining arguments (one-line description, may be empty)

Validate `SKILL_NAME`:
- Lowercase letters, numbers, and hyphens only
- Max 64 characters
- Must not be empty

Check if `~/.claude/skills/{SKILL_NAME}` already exists. If so, ask user: update or abort?

## Step 2: Clarification Interview

Ask the user up to 3 questions (skip any already answered by the arguments):

1. **Purpose**: "What should this skill do? Describe the primary use case in 1-2 sentences."
   - Skip if `DESCRIPTION` is already clear and specific

2. **Invocation mode**: "How should it be triggered?"
   - (a) User-only via `/slash-command` — for side effects (creates files, deploys, sends)
   - (b) Both user and Claude — general purpose
   - (c) Claude-only, hidden from user — background knowledge

3. **Tools and dependencies**: "Does it need scripts, APIs, or specific tools?"
   - Help the user identify which `allowed-tools` are needed
   - Apply principle of least privilege

Based on answers, determine all frontmatter fields.
For the full field reference, read `references/frontmatter-fields.md`.

## Step 3: Plan and Confirm

Present the plan to the user before creating anything:

```
Plan for skill "{SKILL_NAME}":

Frontmatter:
  name: {SKILL_NAME}
  description: {DESCRIPTION} (X chars)
  disable-model-invocation: {true/false}
  allowed-tools: {list}
  {other fields if applicable}

Directories: {list only what's needed}
IMPROVEMENTS.md: included

Proceed? [y/n]
```

Wait for confirmation before continuing.

## Step 4: Create the Skill

### 4a. Directory structure

Create only directories that will contain files:
```bash
mkdir -p ~/.claude/skills/{SKILL_NAME}
# Only create subdirectories if they'll have content:
# mkdir -p ~/.claude/skills/{SKILL_NAME}/references
# mkdir -p ~/.claude/skills/{SKILL_NAME}/scripts
# mkdir -p ~/.claude/skills/{SKILL_NAME}/examples
```

### 4b. Write SKILL.md

Generate the SKILL.md with:
- YAML frontmatter with all determined fields
- Markdown body in imperative form
- Under 500 lines total
- References to supporting files if they exist
- Self-Improvement Protocol section at the end (see below)

Follow the body writing rules from `references/spec.md`.
Choose the appropriate skill pattern from `references/patterns.md`.

**Always include this section at the end of the body:**

```markdown
## Self-Improvement Protocol
When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for {SKILL_NAME}"
```

### 4c. Write IMPROVEMENTS.md

```markdown
# Improvements Log for {SKILL_NAME}

Claude logs observations and improvement ideas here.
DO NOT modify SKILL.md directly. The user reviews and promotes changes.

## Format

- **Date**: YYYY-MM-DD
- **Context**: What was happening when the insight occurred
- **Observation**: What could be improved
- **Suggested change**: Concrete proposal

---

<!-- Entries below this line -->
```

### 4d. Supporting files (optional)

Only create if the skill needs them:
- `references/` — for detailed specs, API docs, field references
- `scripts/` — for executable automation (make executable with `chmod +x`)
- `examples/` — for sample inputs/outputs

## Step 5: Validate

Run the validation script against the new skill:

```bash
~/.claude/skills/meta-skill-creator/scripts/validate_skill.sh ~/.claude/skills/{SKILL_NAME}
```

Review the checklist from `references/checklist.md`.

If validation fails, fix issues and re-validate.

## Step 6: Summary

Show the created structure:

```bash
find ~/.claude/skills/{SKILL_NAME} -type f
```

Tell the user:
- How to test: `/skill-name [arguments]`
- How evolution works: "Claude will log improvement ideas to IMPROVEMENTS.md. Review and promote changes when ready."

## Self-Improvement Protocol

When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for meta-skill-creator"
