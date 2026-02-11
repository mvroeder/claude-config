# Skill Type Patterns

Four common skill archetypes with recommended configurations.

## 1. Reference Skill (Conventions, Style Guides)

**Purpose**: Inject domain knowledge into Claude's context.

**Configuration**:
```yaml
---
name: api-conventions
description: API design conventions for this project. Loaded automatically when writing or reviewing API code.
user-invocable: false
allowed-tools: Read, Grep, Glob
---
```

**Characteristics**:
- No side effects
- Claude loads automatically when relevant
- Body contains rules, not workflows
- Often `user-invocable: false` (no slash command needed)

---

## 2. Task Skill (Deploy, Commit, Build)

**Purpose**: Execute a multi-step workflow with side effects.

**Configuration**:
```yaml
---
name: deploy
description: Deploy the application to staging or production. Use when the user asks to deploy or ship.
disable-model-invocation: true
allowed-tools: Bash, Read
---
```

**Characteristics**:
- Has side effects (creates, modifies, sends)
- Always `disable-model-invocation: true`
- Body is a step-by-step workflow
- `allowed-tools` strictly limited

---

## 3. Research/Analysis Skill

**Purpose**: Investigate, analyze, and report without modifying anything.

**Configuration**:
```yaml
---
name: code-review
description: Review code changes for bugs, style, and best practices. Use when reviewing PRs or before merging.
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash
---
```

**Characteristics**:
- Read-only, no side effects
- Often `context: fork` for isolation
- Body describes what to look for and how to report
- Can use dynamic context injection: `!`gh pr diff``

---

## 4. Generator Skill (Scaffold, Create)

**Purpose**: Create new files, components, or structures.

**Configuration**:
```yaml
---
name: new-component
description: Scaffold a new React component with tests and stories. Use when creating new UI components.
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Glob, Grep
---
```

**Characteristics**:
- Creates files (side effect) → `disable-model-invocation: true`
- Body contains templates and generation rules
- Often uses `$ARGUMENTS` for the component name
- Validates output after creation

---

## Choosing a Pattern

```
Does the skill modify files or external state?
├── YES → Does it need user confirmation?
│   ├── YES → Task Skill or Generator Skill
│   │   └── Creates new structure? → Generator
│   │   └── Executes workflow? → Task
│   └── NO → (rare — almost always needs confirmation)
└── NO → Does it provide background knowledge?
    ├── YES → Reference Skill
    └── NO → Research/Analysis Skill
```

## Composing Skills

Prefer multiple focused skills over one monolith:

**Bad**: One `project-manager` skill that handles setup, review, deploy, and testing.

**Good**:
- `project-setup` — scaffold new projects
- `code-review` — review changes
- `deploy` — ship to production
- `test-runner` — run and report tests

Each skill does one thing well. Claude activates the right one based on context.

## Self-Evolution Pattern

Every skill gets an IMPROVEMENTS.md. The protocol in SKILL.md:

```markdown
## Self-Improvement Protocol
When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for {skill-name}"
```

This creates a feedback loop without autonomous skill modification.
