---
name: yt-summarize
description: Transcribe and summarize YouTube videos using yt-dlp + Claude API with Whisper fallback. Use when user shares a YouTube URL or asks to summarize a video.
argument-hint: '<youtube-url> [--lang de,en] [--whisper] [--transcript-only]'
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# YouTube Video Transcribe & Summarize

Transcribe a YouTube video and generate a structured summary using Claude.

## Prerequisites

Check that required tools are available before starting:

```bash
which yt-dlp || echo "MISSING: yt-dlp — install with: uv pip install yt-dlp"
```

If `--whisper` is used or subtitle fallback is needed:
```bash
which whisper || echo "MISSING: whisper — install with: uv pip install openai-whisper"
```

## Step 1: Parse Arguments

Extract from `$ARGUMENTS`:
- **URL** (required): YouTube URL or video ID — first positional argument
- **--lang**: Subtitle languages, comma-separated (default: `de,en`)
- **--whisper**: Force Whisper transcription instead of YouTube subtitles
- **--transcript-only**: Output transcript without summarization
- **--summary-lang**: Language for the summary (default: `Deutsch`)
- **--model**: Claude model for summarization (default: `claude-sonnet-4-6`)

If no URL is provided, ask the user for one.

## Step 2: Transcribe

Run the script to get the transcript. Use the hybrid approach:

### Default: YouTube Subtitles First
```bash
python3 ~/.claude/skills/yt-summarize/scripts/yt-summarize.py "$URL" --lang "$LANG" --transcript-only
```

### Fallback or --whisper: Whisper Transcription
If subtitles are unavailable or `--whisper` was specified:
```bash
python3 ~/.claude/skills/yt-summarize/scripts/yt-summarize.py "$URL" --whisper --transcript-only
```

The script handles the hybrid logic internally:
1. Try YouTube auto-subtitles via yt-dlp
2. If no subtitles found and Whisper is available → download audio and transcribe
3. If `--whisper` flag → skip subtitles, go straight to Whisper

## Step 3: Summarize

If `--transcript-only` was NOT set, run the full pipeline:
```bash
python3 ~/.claude/skills/yt-summarize/scripts/yt-summarize.py "$URL" --lang "$LANG" --summary-lang "$SUMMARY_LANG" --model "$MODEL"
```

Display the structured summary to the user. The summary includes:
1. **Kernaussagen** — 3-5 key points
2. **Zusammenfassung** — Concise summary (max 300 words)
3. **Interessante Details** — Notable quotes, data points, insights
4. **Fazit** — One-sentence takeaway

## Step 4: Output

Present the result clearly formatted. If the transcript is very long (>50,000 chars), warn the user about potential token usage before summarizing.

## Error Handling

- **No yt-dlp**: Tell user to install with `uv pip install yt-dlp`
- **No whisper**: Tell user to install with `uv pip install openai-whisper`
- **No ANTHROPIC_API_KEY**: Remind user to set it (only needed for summarization)
- **No subtitles + no Whisper**: Inform user that neither method worked and suggest installing Whisper
- **Private/unavailable video**: Report the yt-dlp error clearly

## Self-Improvement Protocol

When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for yt-summarize"
