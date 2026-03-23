---
name: yt-transcribe
description: Transcribe a single YouTube video using yt-dlp subtitles or audio engines (Whisper, OpenAI API). Outputs plain text or JSON. Use when user wants a transcript without summarization.
argument-hint: '<youtube-url> [--engine whisper|whisper-api|gpt4o-transcribe] [--format plain|json]'
disable-model-invocation: true
allowed-tools: Bash, Read, AskUserQuestion
---

# YouTube Video Transcribe

Transcribe a single YouTube video. No summarization, no playlist support — just the transcript.

## Prerequisites

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
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+set}"
```

## Step 1: Parse Arguments

Extract from `$ARGUMENTS`:
- **URL** (required): YouTube video URL or video ID
- **--engine**: `auto` (default), `whisper`, `whisper-api`, `gpt4o-transcribe`
- **--whisper**: Shortcut for `--engine whisper`
- **--lang**: Subtitle languages, comma-separated (default: `de,en`)
- **--format**: `plain` (default) or `json`

If no URL is provided, ask the user for one.

### Engine Options

| Engine | Description | Requirements |
|--------|-------------|--------------|
| `auto` | Subtitles first, then fallback | yt-dlp |
| `whisper` | Local Whisper transcription | `openai-whisper` |
| `whisper-api` | OpenAI Whisper API (~$0.006/min) | `openai`, `OPENAI_API_KEY` |
| `gpt4o-transcribe` | GPT-4o Transcribe (~$0.006/min, best quality) | `openai`, `OPENAI_API_KEY` |

## Step 2: Transcribe

Run the script. Use `$CLAUDE_PLUGIN_ROOT` for the script path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/yt-transcribe}/scripts/yt-transcribe.py" "$URL" --engine "$ENGINE" --lang "$LANG" --format "$FORMAT"
```

**Non-interactive fallback handling (exit code 2):**

In auto mode, if no subtitles are found and the script cannot prompt interactively, it exits with code 2 and prints available engines as JSON to stderr.

When exit code is 2:
1. Parse the JSON from stderr to get available engines
2. Use `AskUserQuestion` to ask the user which engine to use
3. Re-run with `--engine <chosen_engine>`

## Step 3: Output

- **plain**: Raw transcript text on stdout — pipe-friendly
- **json**: Structured object: `{ "video_id", "title", "url", "engine", "transcript", "char_count" }`

Present the result to the user. For very long transcripts (>50,000 chars), mention the length.

## Error Handling

- **No yt-dlp**: Tell user to install with `uv pip install yt-dlp`
- **No whisper**: Tell user to install with `uv pip install openai-whisper`
- **No openai**: Tell user to install with `uv pip install openai`
- **No OPENAI_API_KEY**: Remind user to set it
- **Exit code 2**: Engine selection needed — use AskUserQuestion
- **Timeout**: Report which command timed out and suggest retry
- **Private/unavailable video**: Report the yt-dlp error clearly
