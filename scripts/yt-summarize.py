#!/usr/bin/env python3
"""Transcribe and summarize YouTube videos using yt-dlp + Claude API."""

import argparse
import os
import re
import subprocess
import sys
import tempfile

try:
    import anthropic
except ImportError:
    print("Missing dependency: anthropic")
    print("Install with: uv pip install anthropic")
    sys.exit(1)


def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def get_video_title(url: str) -> str:
    """Fetch the video title via yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--get-title", "--no-warnings", url],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "Unknown Title"


def fetch_transcript(url: str, languages: list[str]) -> str:
    """Download auto-generated subtitles via yt-dlp and return as plain text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_template = os.path.join(tmpdir, "subs")
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang",
            ",".join(languages),
            "--skip-download",
            "--sub-format",
            "vtt",
            "-o",
            out_template,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"yt-dlp failed: {result.stderr.strip() or 'unknown error'}"
            )

        # Find the downloaded subtitle file
        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            raise FileNotFoundError(
                "No subtitles found. The video may not have captions."
            )

        vtt_path = os.path.join(tmpdir, vtt_files[0])
        return vtt_to_plain_text(vtt_path)


def vtt_to_plain_text(path: str) -> str:
    """Convert a .vtt subtitle file to clean plain text."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    text_lines: list[str] = []
    seen: set[str] = set()

    for line in lines:
        line = line.strip()
        # Skip VTT headers, timestamps, and empty lines
        if (
            not line
            or line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or re.match(r"\d{2}:\d{2}", line)
            or "-->" in line
        ):
            continue
        # Strip VTT tags like <c> </c> <00:00:01.234>
        line = re.sub(r"<[^>]+>", "", line)
        # Deduplicate repeated lines (common in auto-subs)
        if line not in seen:
            seen.add(line)
            text_lines.append(line)

    return " ".join(text_lines)


def summarize(transcript: str, title: str, language: str, model: str) -> str:
    """Send the transcript to Claude for summarization."""
    client = anthropic.Anthropic()

    prompt = f"""Here is the transcript of a YouTube video titled "{title}".
Please provide a structured summary in {language}:

1. **Kernaussagen** — The 3-5 most important points
2. **Zusammenfassung** — A concise summary (max 300 words)
3. **Interessante Details** — Notable quotes, data points, or insights
4. **Fazit** — One-sentence takeaway

Transcript:
{transcript}"""

    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe and summarize YouTube videos with Claude"
    )
    parser.add_argument("url", help="YouTube video URL or video ID")
    parser.add_argument(
        "--lang",
        default="de,en",
        help="Subtitle languages, comma-separated (default: de,en)",
    )
    parser.add_argument(
        "--summary-lang",
        default="Deutsch",
        help="Language for the summary output (default: Deutsch)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Claude model to use (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--transcript-only",
        action="store_true",
        help="Only output the transcript, skip summarization",
    )
    args = parser.parse_args()

    # Check yt-dlp is installed
    if not subprocess.run(["which", "yt-dlp"], capture_output=True).returncode == 0:
        print("Error: yt-dlp not found. Install with: uv pip install yt-dlp")
        sys.exit(1)

    # Check API key unless transcript-only
    if not args.transcript_only and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set.")
        print("Export it or add to .env: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    languages = [lang.strip() for lang in args.lang.split(",")]

    print(f"Fetching video title...")
    title = get_video_title(args.url)
    print(f"Title: {title}\n")

    print(f"Extracting transcript ({', '.join(languages)})...")
    transcript = fetch_transcript(args.url, languages)
    print(f"Transcript: {len(transcript)} characters\n")

    if args.transcript_only:
        print(transcript)
        return

    print(f"Summarizing with {args.model}...")
    summary = summarize(transcript, title, args.summary_lang, args.model)
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")
    print(summary)


if __name__ == "__main__":
    main()
