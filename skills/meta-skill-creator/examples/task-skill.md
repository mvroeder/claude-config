# Example: Task Skill with Side Effects

A skill that performs actions requiring explicit user invocation.

## Structure

```
~/.claude/skills/deploy/
├── SKILL.md
├── IMPROVEMENTS.md
└── references/
    └── environments.md
```

## SKILL.md

```yaml
---
name: deploy
description: Deploy the application to staging or production. Use when the user asks to deploy, ship, or release.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep
argument-hint: '[environment: staging|production]'
---
```

```markdown
Deploy $ARGUMENTS[0] (default: staging).

## Pre-flight checks

1. Verify clean working tree: `git status --porcelain`
2. Run test suite: `npm test`
3. Check current branch matches expected deployment branch
4. For production: confirm with user before proceeding

## Deploy

1. Build: `npm run build`
2. Push to deployment target for the environment
3. For environment details, read `references/environments.md`

## Post-deploy

1. Verify deployment health check passes
2. Report status: environment, commit SHA, URL, duration

## Self-Improvement Protocol
When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for deploy"
```

## Why this works

- `disable-model-invocation: true` — deploys are destructive, user must invoke
- `allowed-tools` excludes Write (deploy doesn't create local files)
- `argument-hint` shows the user what arguments are expected
- References environment details in a separate file (keeps SKILL.md lean)
- Production deploy requires explicit user confirmation
