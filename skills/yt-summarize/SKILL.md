---
name: yt-summarize
description: Transcribe and summarize YouTube videos using yt-dlp + Claude API with multiple transcription engines. Use when user shares a YouTube URL or asks to summarize a video.
argument-hint: '<youtube-url> [--lang de,en] [--engine whisper|whisper-api|gpt4o-transcribe] [--transcript-only]'
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
- **--lang**: Subtitle languages, comma-separated (default: `de,en`)
- **--engine**: Transcription engine — `auto` (default), `whisper`, `whisper-api`, `gpt4o-transcribe`
- **--whisper**: Shortcut for `--engine whisper`
- **--transcript-only**: Output transcript without summarization
- **--summary-lang**: Language for the summary (default: `Deutsch`)
- **--model**: Claude model for summarization (default: `claude-sonnet-4-6`)

If no URL is provided, ask the user for one.

### Engine Options

| Engine | Description | Requirements |
|--------|-------------|--------------|
| `auto` | Subtitles first, then interactive choice | yt-dlp |
| `whisper` | Local Whisper transcription | `openai-whisper` |
| `whisper-api` | OpenAI Whisper API (~$0.006/min) | `openai`, `OPENAI_API_KEY` |
| `gpt4o-transcribe` | GPT-4o Transcribe (~$0.006/min, best quality) | `openai`, `OPENAI_API_KEY` |

## Step 2: Transcribe

Run the script to get the transcript:

### With specific engine:
```bash
python3 ~/.claude/skills/yt-summarize/scripts/yt-summarize.py "$URL" --engine "$ENGINE" --transcript-only
```

### Auto mode (default — subtitles first, then interactive):
```bash
python3 ~/.claude/skills/yt-summarize/scripts/yt-summarize.py "$URL" --lang "$LANG" --transcript-only
```

The auto mode logic:
1. Try YouTube auto-subtitles via yt-dlp
2. If no subtitles found → show available engines and let user choose interactively
3. Available engines depend on installed packages and set API keys

**IMPORTANT**: In auto mode, the script uses `input()` for interactive choice. When running via Bash tool, the script may not be able to prompt interactively. In that case, either:
- Specify `--engine` explicitly, or
- Use AskUserQuestion to ask the user which engine to use, then pass the choice via `--engine`

## Step 3: Summarize

If `--transcript-only` was NOT set, run the full pipeline:
```bash
python3 ~/.claude/skills/yt-summarize/scripts/yt-summarize.py "$URL" --lang "$LANG" --engine "$ENGINE" --summary-lang "$SUMMARY_LANG" --model "$MODEL"
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
- **No openai**: Tell user to install with `uv pip install openai`
- **No ANTHROPIC_API_KEY**: Remind user to set it (only needed for summarization)
- **No OPENAI_API_KEY**: Remind user to set it (only needed for API engines)
- **No engines available**: Suggest installing either whisper or openai package
- **Private/unavailable video**: Report the yt-dlp error clearly

## Self-Improvement Protocol

When you notice something that would improve this skill:
1. Append the insight to IMPROVEMENTS.md with date and context
2. Do NOT modify SKILL.md directly
3. Tell the user: "I logged a potential improvement for yt-summarize"
