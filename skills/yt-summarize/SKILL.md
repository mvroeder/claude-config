---
name: yt-summarize
description: Summarize YouTube videos or playlists using yt-transcribe + Claude API with multiple summary modes (kurz/standard/learn). Use when user shares a YouTube URL, playlist URL, or asks to summarize a video. Requires yt-transcribe skill for transcription.
argument-hint: '<youtube-url-or-playlist> [--mode kurz|standard|learn] [--engine whisper|whisper-api|gpt4o-transcribe]'
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion, Grep, Glob
---

# YouTube Video Summarize

Summarize YouTube videos (single or playlist) using Claude. Transcription is delegated to the **yt-transcribe** skill (called as subprocess).

## Prerequisites

Check that required tools are available before starting:

```bash
# yt-transcribe skill must be installed
TRANSCRIBE_SCRIPT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/yt-summarize}/../yt-transcribe/scripts/yt-transcribe.py"
test -f "$TRANSCRIBE_SCRIPT" && echo "yt-transcribe: OK" || echo "MISSING: yt-transcribe skill"
which yt-dlp || echo "MISSING: yt-dlp — install with: uv pip install yt-dlp"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+set}"
```

## Step 1: Parse Arguments

Extract from `$ARGUMENTS`:
- **URL** (required): YouTube video URL, video ID, or **playlist URL** — first positional argument
- **--mode**: Summary mode — `kurz` (brief), `standard` (default), `learn`
- **--lang**: Subtitle languages, comma-separated (default: `de,en`)
- **--engine**: Transcription engine (passed to yt-transcribe) — `auto` (default), `whisper`, `whisper-api`, `gpt4o-transcribe`
- **--whisper**: Shortcut for `--engine whisper`
- **--transcript-only**: Output transcript without summarization (still uses yt-transcribe)
- **--summary-lang**: Language for the summary (default: `Deutsch`)
- **--model**: Claude model for summarization (default: `claude-sonnet-4-6`)
- **--save-learnings**: Save learn mode output to knowledge base

If no URL is provided, ask the user for one.

### Summary Modes

| Mode | Description | Output |
|------|-------------|--------|
| `kurz` | Quick overview | Kernaussagen, Zusammenfassung (300 words), Details, Fazit |
| `standard` | Comprehensive analysis (default) | Up to 2000 words with context, quotes, critical analysis |
| `learn` | Extract learnings | Key principles, actionable items, skill matching, JSON+MD |

### Engine Options

| Engine | Description | Requirements |
|--------|-------------|--------------|
| `auto` | Subtitles first, then fallback | yt-dlp |
| `whisper` | Local Whisper transcription | `openai-whisper` |
| `whisper-api` | OpenAI Whisper API (~$0.006/min) | `openai`, `OPENAI_API_KEY` |
| `gpt4o-transcribe` | GPT-4o Transcribe (~$0.006/min, best quality) | `openai`, `OPENAI_API_KEY` |

### Playlist Support

The script auto-detects playlist URLs (containing `list=` or `/playlist?`). When a playlist URL is provided:
- All videos are extracted using `yt-dlp --flat-playlist`
- Each video is processed sequentially (transcribe → summarize)
- Errors on individual videos are logged but don't stop the playlist
- A final summary shows succeeded/failed counts

The script handles everything — just pass the playlist URL as the `url` argument. All flags (`--mode`, `--engine`, `--save-learnings`, etc.) apply to every video in the playlist.

**For the interest feedback loop (Step 5)**: When processing a playlist, ask for interest feedback **once at the end** covering all videos, not after each individual video. Summarize the main topics across all videos and let the user rate overall.

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
