---
name: yt-summarize
description: Transcribe and summarize YouTube videos using yt-dlp + Claude API with multiple transcription engines and summary modes (kurz/standard/learn). Use when user shares a YouTube URL or asks to summarize a video.
argument-hint: '<youtube-url> [--mode kurz|standard|learn] [--engine whisper|whisper-api|gpt4o-transcribe]'
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion, Grep, Glob
---

# YouTube Video Transcribe & Summarize

Transcribe a YouTube video and generate a personalized, structured summary using Claude.

## Prerequisites

Check that required tools are available before starting:

```bash
which yt-dlp || echo "MISSING: yt-dlp — install with: uv pip install yt-dlp"
```

Optional (for local Whisper):
```bash
which whisper || echo "OPTIONAL: whisper — install with: uv pip install openai-whisper"
```

Optional (for OpenAI API engines):
```bash
python3 -c "import openai" 2>/dev/null || echo "OPTIONAL: openai — install with: uv pip install openai"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+set}" # Never show the actual key
```

## Step 1: Parse Arguments

Extract from `$ARGUMENTS`:
- **URL** (required): YouTube URL or video ID — first positional argument
- **--mode**: Summary mode — `kurz` (default), `standard`, `learn`
- **--lang**: Subtitle languages, comma-separated (default: `de,en`)
- **--engine**: Transcription engine — `auto` (default), `whisper`, `whisper-api`, `gpt4o-transcribe`
- **--whisper**: Shortcut for `--engine whisper`
- **--transcript-only**: Output transcript without summarization
- **--summary-lang**: Language for the summary (default: `Deutsch`)
- **--model**: Claude model for summarization (default: `claude-sonnet-4-6`)
- **--save-learnings**: Save learn mode output to knowledge base

If no URL is provided, ask the user for one.

### Summary Modes

| Mode | Description | Output |
|------|-------------|--------|
| `kurz` | Quick overview (default) | Kernaussagen, Zusammenfassung (300 words), Details, Fazit |
| `standard` | Comprehensive analysis | Up to 2000 words with context, quotes, critical analysis |
| `learn` | Extract learnings | Key principles, actionable items, skill matching, JSON+MD |

### Engine Options

| Engine | Description | Requirements |
|--------|-------------|--------------|
| `auto` | Subtitles first, then fallback | yt-dlp |
| `whisper` | Local Whisper transcription | `openai-whisper` |
| `whisper-api` | OpenAI Whisper API (~$0.006/min) | `openai`, `OPENAI_API_KEY` |
| `gpt4o-transcribe` | GPT-4o Transcribe (~$0.006/min, best quality) | `openai`, `OPENAI_API_KEY` |

## Step 2: Transcribe

Run the script to get the transcript. Use `$CLAUDE_PLUGIN_ROOT` for the script path:

### With specific engine:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/yt-summarize}/scripts/yt-summarize.py" "$URL" --engine "$ENGINE" --transcript-only
```

### Auto mode (default — subtitles first, then fallback):
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/yt-summarize}/scripts/yt-summarize.py" "$URL" --lang "$LANG" --transcript-only
```

**IMPORTANT: Non-interactive fallback handling**

In auto mode, if no subtitles are found and the script cannot prompt interactively (no TTY), it exits with **code 2** and prints available engines as JSON to stderr.

When exit code is 2:
1. Parse the JSON from stderr to get available engines
2. Use `AskUserQuestion` to ask the user which engine to use
3. Re-run with `--engine <chosen_engine>`

## Step 3: Summarize

Run the full pipeline with the chosen mode:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/yt-summarize}/scripts/yt-summarize.py" "$URL" --mode "$MODE" --lang "$LANG" --engine "$ENGINE" --summary-lang "$SUMMARY_LANG" --model "$MODEL"
```

For learn mode with knowledge base saving:
```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/yt-summarize}/scripts/yt-summarize.py" "$URL" --mode learn --save-learnings
```

## Step 4: Output

Present the result clearly formatted. If the transcript is very long (>50,000 chars), warn the user about potential token usage before summarizing.

### Mode-specific output:

**kurz**: Display the summary directly.

**standard**: Display the summary. Due to length (~2000 words), consider using a collapsible section or clear heading structure.

**learn**: Display the learning summary. If `--save-learnings` was used, inform the user where files were saved. If skill matches were found, highlight them.

## Step 5: Interest Feedback Loop

**After presenting ANY summary (all modes), always do this:**

1. Use `AskUserQuestion` to ask:
   > "Wie interessant war dieses Video für dich?"
   Options:
   - **Kein Interesse** — "Thema ist nicht relevant für mich"
   - **Wenig Interesse** — "Etwas relevant, aber keine Priorität"
   - **Hohes Interesse** — "Sehr relevant, mehr davon!"

2. Based on the response, update INTERESTS.md:
   - Read the current `INTERESTS.md` from the repo (find it via `$CLAUDE_CONFIG_REPO/INTERESTS.md` or search for it)
   - Extract the main topics/tags from the video summary
   - **Hohes Interesse**: Add or reinforce topics under `## Topics of Interest` with today's date
     - If topic already exists, add today's date as `reinforced: YYYY-MM-DD`
     - If new topic, add as `(added: YYYY-MM-DD)`
   - **Kein Interesse**: Add topics under `## Not Interested` with `(since: YYYY-MM-DD)`
   - **Wenig Interesse**: No changes (neutral signal)

3. If INTERESTS.md was changed:
   - Write the updated file
   - Commit with message: `chore: update INTERESTS.md from yt-summarize feedback`
   - Tell the user: "Dein Interessenprofil wurde aktualisiert."

## Error Handling

- **No yt-dlp**: Tell user to install with `uv pip install yt-dlp`
- **No whisper**: Tell user to install with `uv pip install openai-whisper`
- **No openai**: Tell user to install with `uv pip install openai`
- **No ANTHROPIC_API_KEY**: Remind user to set it (only needed for summarization)
- **No OPENAI_API_KEY**: Remind user to set it (only needed for API engines)
- **No engines available**: Suggest installing either whisper or openai package
- **Exit code 2**: Engine selection needed — use AskUserQuestion (see Step 2)
- **Timeout**: Report which command timed out and suggest retry
- **Private/unavailable video**: Report the yt-dlp error clearly

## Self-Improvement Protocol

When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for yt-summarize"
