# claude-config

A central configuration repository for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that manages **custom skills**, **hooks**, and **preferences** — synced automatically across all projects and machines.

## What This Does

Claude Code supports user-defined **skills** (reusable prompt-based capabilities) and **hooks** (scripts triggered by lifecycle events). This repository:

1. **Stores skills in version control** — single source of truth, no manual copying.
2. **Auto-syncs skills** on every Claude Code session start, on any project.
3. **Works across machines** — clone the repo, run `install.sh` once, done.

```
┌─────────────────────────────────────────────────────────┐
│  claude-config repo (~/dev/claude-config)               │
│                                                         │
│  skills/           scripts/           hooks/            │
│  ├── last30days/   ├── install.sh     └── global-       │
│  ├── yt-summarize/ └── sync-skills.sh     session-      │
│  └── meta-skill-creator/                  start.sh      │
└──────────────┬──────────────────────────────────────────┘
               │ install.sh (once per machine)
               ▼
┌──────────────────────────────────┐
│  ~/.claude/                      │
│  ├── hooks/session-start.sh      │  ← stable entry point
│  └── settings.json               │    (SessionStart hook)
└──────────────┬───────────────────┘
               │ every session start
               │ (prerequisite checks + git pull + copy)
               ▼
┌──────────────────────────┐
│  ~/.claude/skills/       │  ← Claude Code reads
│  ├── last30days/         │    skills from here
│  ├── yt-summarize/       │
│  └── meta-skill-creator/ │
└──────────────────────────┘
```

## Setup

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- `git` and `jq` available on the system

### Installation (once per machine)

```bash
# 1. Clone the repo
git clone git@github.com:mvroeder/claude-config.git ~/dev/claude-config

# 2. Set the environment variable (add to ~/.zshrc or ~/.bashrc)
export CLAUDE_CONFIG_REPO="$HOME/dev/claude-config"

# 3. Reload shell
source ~/.zshrc

# 4. Run the install script
$CLAUDE_CONFIG_REPO/scripts/install.sh
```

The install script:
1. Copies `hooks/global-session-start.sh` to `~/.claude/hooks/session-start.sh`
2. Registers a **user-level SessionStart hook** in `~/.claude/settings.json`

From now on, every Claude Code session automatically pulls the latest changes and copies skills to `~/.claude/skills/`.

### What Happens on Every Session Start

1. `~/.claude/hooks/session-start.sh` runs automatically.
2. It **checks prerequisites** and aborts with a clear error if something is missing:
   - `CLAUDE_CONFIG_REPO` env var must be set
   - The repo directory must exist
   - `sync-skills.sh` must be executable
3. It warns (non-fatal) if `~/.claude/CLAUDE.md` or `~/.claude/skills/` are missing.
4. It delegates to `sync-skills.sh`, which does a quick `git pull --ff-only` (timeout 10s, fails silently if offline).
5. Each skill directory is compared by timestamp — only changed skills are copied.
6. Skills are available immediately via `/skill-name` in Claude Code.

## Skills

### `/last30days` — Topic Research

Research a topic across Reddit, X (Twitter), and the web from the last 30 days. Returns curated findings with engagement metrics.

```
/last30days best AI video tools 2026
/last30days --quick NVIDIA news
/last30days nano banana pro prompts --deep
```

**Features:**
- Multi-source search (Reddit, X, Web) with engagement scoring
- Three speed modes: `--quick`, default, `--deep`
- Configurable lookback window: `--days=N`
- Works with no API keys (WebSearch fallback) or with OpenAI/xAI keys for richer results

**Requires:** Python environment with dependencies (see `skills/last30days/scripts/`)

### `/yt-summarize` — YouTube Transcription & Summary

Transcribe and summarize YouTube videos. Outputs structured German summaries (key points, summary, notable details, conclusion).

```
/yt-summarize https://www.youtube.com/watch?v=...
/yt-summarize <url> --engine gpt4o-transcribe
/yt-summarize <url> --transcript-only --lang en
```

**Transcription engines:**
| Engine | Cost | Speed | Quality |
|---|---|---|---|
| Subtitles (auto) | Free | Instant | Varies |
| Whisper (local) | Free | Slow | Good |
| Whisper API | $0.006/min | Fast | Good |
| GPT-4o Transcribe | $0.006/min | Fast | Best |

**Requires:** `yt-dlp`, optionally `openai-whisper` for local transcription, `OPENAI_API_KEY` for API-based engines.

### `/meta-skill-creator` — Skill Scaffolding

Interactively create new Claude Code skills with proper structure, frontmatter, and best practices.

```
/meta-skill-creator deploy-checker "Check deployment status across environments"
/meta-skill-creator
```

**What it generates:**
```
~/.claude/skills/<skill-name>/
├── SKILL.md           # Frontmatter + instructions
├── IMPROVEMENTS.md    # Evolution log
└── references/        # Optional: detailed docs
```

Includes an interactive interview to determine trigger mode, required tools, and skill pattern (reference, task, research, or generator).

## Repository Structure

```
claude-config/
├── CLAUDE.md                        # Global preferences (synced to ~/.claude/CLAUDE.md)
├── README.md                        # This file
├── .gitignore                       # Reverse-ignore: only whitelist what should be tracked
│
├── hooks/
│   └── global-session-start.sh      # Global hook source — installed by install.sh
│
├── templates/
│   ├── CLAUDE-coding.md             # Project template: coding & architecture
│   └── CLAUDE-writing.md            # Project template: PRDs, whitepapers, docs
│
├── scripts/
│   ├── install.sh                   # One-time setup: install hook + register in settings.json
│   └── sync-skills.sh               # Sync skills from repo to ~/.claude/skills/
│
├── skills/
│   ├── last30days/                  # Topic research skill
│   │   ├── SKILL.md
│   │   ├── scripts/                 # Python orchestrator + library modules
│   │   └── tests/                   # Unit tests
│   ├── yt-summarize/                # YouTube transcription skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   └── meta-skill-creator/          # Skill scaffolding skill
│       ├── SKILL.md
│       ├── references/              # Spec, patterns, checklist
│       ├── examples/                # Example skill templates
│       └── scripts/
│
└── .claude/
    ├── hooks/
    │   └── session-start.sh         # Project-level hook (for development)
    └── settings.json                # Project-level hook registration
```

## Adding a New Skill

1. Create the skill (easiest via `/meta-skill-creator`), or manually:
   ```bash
   mkdir -p skills/my-skill
   # Write skills/my-skill/SKILL.md with YAML frontmatter
   touch skills/my-skill/IMPROVEMENTS.md
   ```

2. Commit and push:
   ```bash
   cd ~/dev/claude-config
   git add skills/my-skill/
   git commit -m "feat: add my-skill"
   git push
   ```

3. Next Claude Code session on any machine picks it up automatically.

## Design Decisions

**No absolute paths in config.** Everything uses environment variables (`$CLAUDE_CONFIG_REPO`, `$CLAUDE_PROJECT_DIR`) so the setup works across machines without modification.

**Reverse-ignore `.gitignore`.** The gitignore blocks everything by default and explicitly whitelists tracked directories. This prevents secrets, caches, audio files, and other artifacts from being accidentally committed.

**Stable hook entry point.** The SessionStart hook is installed to `~/.claude/hooks/session-start.sh` — a path that relies only on `$HOME`, which is always available. The old approach referenced `$CLAUDE_CONFIG_REPO` directly in `settings.json`, which caused a silent failure if the env var wasn't set. The hook now fails loudly with actionable error messages instead.

**Two-layer hooks.** A *project-level* hook (`.claude/hooks/session-start.sh`) handles syncing during development inside the repo itself. A *user-level* hook (`~/.claude/hooks/session-start.sh`, installed by `install.sh`) handles syncing from any other project.

**Smart copy, not symlinks.** `sync-skills.sh` copies skill directories instead of symlinking. This avoids issues with Claude Code's file resolution and allows timestamp-based change detection to skip unchanged skills.

**Self-evolution pattern.** Every skill includes an `IMPROVEMENTS.md` file. Claude logs observations and suggestions there during use — but never modifies `SKILL.md` directly. The user reviews and promotes improvements when ready.

## CLAUDE.md Hierarchy

Claude Code loads **all** CLAUDE.md files it finds and merges them additively:

| Level | Path | Scope |
|---|---|---|
| Global | `~/.claude/CLAUDE.md` | Every session, every project |
| Project | `<project>/CLAUDE.md` | Only in that project |
| Project (.claude) | `<project>/.claude/CLAUDE.md` | Only in that project |

### Global Preferences (always active)

The global `CLAUDE.md` (managed in this repo, synced to `~/.claude/CLAUDE.md`) contains only universally applicable rules:

- **Responses** in German, **code/commits** in English
- **Conventional Commits** and small commits
- **Secrets** go in `.env`, never committed
- Ask for clarification instead of making assumptions

### Project Templates

For new projects, copy the appropriate template to your project root as `CLAUDE.md`:

```bash
# For coding / architecture projects
cp "$CLAUDE_CONFIG_REPO/templates/CLAUDE-coding.md" ~/dev/my-project/CLAUDE.md

# For writing projects (PRDs, whitepapers, docs)
cp "$CLAUDE_CONFIG_REPO/templates/CLAUDE-writing.md" ~/dev/my-project/CLAUDE.md
```

Then fill in the placeholder sections. The global preferences still apply — the project CLAUDE.md adds project-specific context on top.
