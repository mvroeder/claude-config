# claude-config

Central configuration for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) cloud sessions — manages **custom skills** and **global preferences**, synced automatically via a SessionStart hook.

## How It Works

When a cloud session starts (claude.ai/code), the SessionStart hook:

1. Clones (or pulls) this repo to `~/.claude/claude-config/`
2. Syncs `CLAUDE.md` to `~/.claude/CLAUDE.md`
3. Copies skills to `~/.claude/skills/`

```
Cloud session starts
        │
        ▼
settings.json SessionStart hook
        │
        ├── git clone/pull → ~/.claude/claude-config/
        │
        └── sync-skills.sh
              ├── CLAUDE.md      → ~/.claude/CLAUDE.md
              └── skills/*       → ~/.claude/skills/*
```

## Setup

Add the SessionStart hook from `settings.json` to your project's `.claude/settings.json`:

```json
{
    "hooks": {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "bash -c 'R=\"$HOME/.claude/claude-config\"; if [ -d \"$R/.git\" ]; then timeout 10 git -C \"$R\" pull --ff-only -q 2>/dev/null || true; else timeout 30 git clone --depth 1 -q https://github.com/mvroeder/claude-config.git \"$R\" 2>/dev/null || exit 0; fi; [ -x \"$R/scripts/sync-skills.sh\" ] && exec \"$R/scripts/sync-skills.sh\" || true'"
                    }
                ]
            }
        ]
    }
}
```

## Skills

- **`/last30days`** — Research a topic across Reddit, X, and the web from the last 30 days
- **`/yt-summarize`** — Transcribe and summarize YouTube videos
- **`/meta-skill-creator`** — Interactively scaffold new Claude Code skills

## Adding a New Skill

1. Create a skill directory under `skills/` with a `SKILL.md`
2. Commit and push
3. Next cloud session picks it up automatically

## Repository Structure

```
claude-config/
├── CLAUDE.md              # Global preferences (synced to ~/.claude/CLAUDE.md)
├── settings.json          # SessionStart hook definition
├── scripts/
│   └── sync-skills.sh     # Syncs skills + CLAUDE.md to ~/.claude/
└── skills/
    ├── last30days/
    ├── yt-summarize/
    └── meta-skill-creator/
```
