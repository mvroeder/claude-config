#!/usr/bin/env python3
"""Transcribe a single YouTube video using yt-dlp subtitles or audio engines.

Standalone transcription tool — no summarization, no playlist support.
Outputs plain text (default) or structured JSON to stdout.

Exit codes:
  0 — success
  1 — error (missing dependency, config, etc.)
  2 — engine selection required (non-interactive mode)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import openai as openai_mod
except ImportError:
    openai_mod = None


# ── Custom Exceptions ──


class MissingDependencyError(Exception):
    """Raised when a required dependency is not installed."""


class ConfigError(Exception):
    """Raised when a required configuration (e.g. API key) is missing."""


class EngineSelectionRequired(Exception):
    """Raised in non-interactive mode when the user must choose an engine."""

    def __init__(self, available_engines: dict[str, str]):
        self.available_engines = available_engines
        super().__init__(
            f"Engine selection required. Available: {json.dumps(available_engines)}"
        )


# ── Constants ──

SUBPROCESS_TIMEOUT_SUBTITLE = 120
SUBPROCESS_TIMEOUT_DOWNLOAD = 300
SUBPROCESS_TIMEOUT_WHISPER = 600
SUBPROCESS_TIMEOUT_TITLE = 30

ENGINES = {
    "whisper": "Whisper (local)",
    "whisper-api": "OpenAI Whisper API (~$0.006/min)",
    "gpt4o-transcribe": "GPT-4o Transcribe (~$0.006/min, best quality)",
}


# ── URL helpers ──


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
        timeout=SUBPROCESS_TIMEOUT_TITLE,
    )
    return result.stdout.strip() or "Unknown Title"


# ── VTT parsing ──


def vtt_to_plain_text(path: str) -> str:
    """Convert a .vtt subtitle file to clean plain text."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    text_lines: list[str] = []
    seen: set[str] = set()

    for line in lines:
        line = line.strip()
        if (
            not line
            or line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or re.match(r"\d{2}:\d{2}", line)
            or "-->" in line
        ):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line not in seen:
            seen.add(line)
            text_lines.append(line)

    return " ".join(text_lines)


# ── Transcription engines ──


def fetch_transcript_subtitles(url: str, languages: list[str]) -> str | None:
    """Try to download auto-generated subtitles via yt-dlp. Returns None if unavailable."""
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
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SUBTITLE
        )
        if result.returncode != 0:
            return None

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            return None

        vtt_path = os.path.join(tmpdir, vtt_files[0])
        return vtt_to_plain_text(vtt_path)


def download_audio(url: str, tmpdir: str) -> str:
    """Download audio via yt-dlp and return the file path."""
    audio_path = os.path.join(tmpdir, "audio")
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "-o",
        audio_path + ".%(ext)s",
        url,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_DOWNLOAD
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp audio download failed: {result.stderr.strip() or 'unknown error'}"
        )

    audio_files = [f for f in os.listdir(tmpdir) if f.startswith("audio")]
    if not audio_files:
        raise FileNotFoundError("Audio download produced no output file.")
    return os.path.join(tmpdir, audio_files[0])


def fetch_transcript_whisper(url: str) -> str:
    """Download audio via yt-dlp and transcribe with local Whisper."""
    if not shutil.which("whisper"):
        raise MissingDependencyError(
            "whisper not found. Install with: uv pip install openai-whisper"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = download_audio(url, tmpdir)

        print("Transcribing with Whisper (this may take a while)...", file=sys.stderr)
        result = subprocess.run(
            [
                "whisper",
                audio_file,
                "--model",
                "base",
                "--output_format",
                "txt",
                "--output_dir",
                tmpdir,
            ],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_WHISPER,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Whisper failed: {result.stderr.strip() or 'unknown error'}"
            )

        txt_files = [f for f in os.listdir(tmpdir) if f.endswith(".txt")]
        if not txt_files:
            raise FileNotFoundError("Whisper produced no transcript output.")

        txt_path = os.path.join(tmpdir, txt_files[0])
        with open(txt_path, encoding="utf-8") as f:
            return f.read().strip()


def fetch_transcript_openai_api(url: str, model: str = "whisper-1") -> str:
    """Download audio and transcribe via OpenAI API (Whisper API or GPT-4o-Transcribe)."""
    if openai_mod is None:
        raise MissingDependencyError(
            "Missing dependency: openai. Install with: uv pip install openai"
        )

    if not os.environ.get("OPENAI_API_KEY"):
        raise ConfigError(
            "OPENAI_API_KEY not set. Export it or add to .env: export OPENAI_API_KEY=sk-..."
        )

    client = openai_mod.OpenAI()

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = download_audio(url, tmpdir)

        print(f"Transcribing with {model} API...", file=sys.stderr)
        with open(audio_file, "rb") as af:
            response = client.audio.transcriptions.create(
                model=model,
                file=af,
                response_format="text",
            )

        # response is a string when response_format="text"
        return response.strip() if isinstance(response, str) else response.text.strip()


def transcribe_with_engine(url: str, engine: str) -> str:
    """Transcribe using the specified engine."""
    if engine == "whisper":
        return fetch_transcript_whisper(url)
    elif engine == "whisper-api":
        return fetch_transcript_openai_api(url, model="whisper-1")
    elif engine == "gpt4o-transcribe":
        return fetch_transcript_openai_api(url, model="gpt-4o-transcribe")
    else:
        raise ValueError(f"Unknown engine: {engine}")


# ── Engine selection ──


def get_available_engines() -> dict[str, str]:
    """Return dict of engine_key -> description for currently available engines."""
    available = {}

    if shutil.which("whisper"):
        available["whisper"] = ENGINES["whisper"]

    if openai_mod is not None and os.environ.get("OPENAI_API_KEY"):
        available["whisper-api"] = ENGINES["whisper-api"]
        available["gpt4o-transcribe"] = ENGINES["gpt4o-transcribe"]

    return available


def prompt_engine_choice(available: dict[str, str]) -> str:
    """Ask the user which transcription engine to use.

    In non-interactive mode (no TTY), raises EngineSelectionRequired with
    available engines as JSON on stderr, using exit code 2.
    """
    if not available:
        raise ConfigError(
            "No transcription engine available. Options:\n"
            "  - Install local Whisper: uv pip install openai-whisper\n"
            "  - Set OPENAI_API_KEY for API transcription: uv pip install openai"
        )

    if len(available) == 1:
        key = next(iter(available))
        print(f"Using {available[key]} (only available engine).", file=sys.stderr)
        return key

    # Non-interactive mode: signal that engine selection is needed
    if not sys.stdin.isatty():
        raise EngineSelectionRequired(available)

    print("\nNo subtitles found. Choose a transcription engine:\n", file=sys.stderr)
    keys = list(available.keys())
    for i, key in enumerate(keys, 1):
        print(f"  [{i}] {available[key]}", file=sys.stderr)
    print(file=sys.stderr)

    while True:
        try:
            choice = input(f"Enter choice (1-{len(keys)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {len(keys)}.", file=sys.stderr)


# ── Main logic ──


def transcribe_video(url: str, engine: str, languages: list[str]) -> tuple[str, str]:
    """Transcribe a single video. Returns (transcript, engine_used)."""
    if engine != "auto":
        engine_name = ENGINES.get(engine, engine)
        print(f"Transcribing with {engine_name}...", file=sys.stderr)
        transcript = transcribe_with_engine(url, engine)
        return transcript, engine

    print(f"Extracting subtitles ({', '.join(languages)})...", file=sys.stderr)
    transcript = fetch_transcript_subtitles(url, languages)
    if transcript:
        return transcript, "subtitles"

    available = get_available_engines()
    engine = prompt_engine_choice(available)
    transcript = transcribe_with_engine(url, engine)
    return transcript, engine


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe a single YouTube video"
    )
    parser.add_argument("url", help="YouTube video URL or video ID")
    parser.add_argument(
        "--lang",
        default="de,en",
        help="Subtitle languages, comma-separated (default: de,en)",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "whisper", "whisper-api", "gpt4o-transcribe"],
        default="auto",
        help="Transcription engine (default: auto — subtitles first, then fallback)",
    )
    parser.add_argument(
        "--whisper",
        action="store_true",
        help="Shortcut for --engine whisper",
    )
    parser.add_argument(
        "--format",
        choices=["plain", "json"],
        default="plain",
        dest="output_format",
        help="Output format: plain (default) or json",
    )
    args = parser.parse_args()

    # --whisper flag overrides --engine
    if args.whisper:
        args.engine = "whisper"

    try:
        if not shutil.which("yt-dlp"):
            raise MissingDependencyError(
                "yt-dlp not found. Install with: uv pip install yt-dlp"
            )

        languages = [lang.strip() for lang in args.lang.split(",")]

        print("Fetching video title...", file=sys.stderr)
        title = get_video_title(args.url)
        video_id = extract_video_id(args.url)
        print(f"Title: {title}", file=sys.stderr)

        transcript, engine_used = transcribe_video(args.url, args.engine, languages)
        print(
            f"Transcript ({engine_used}): {len(transcript)} characters",
            file=sys.stderr,
        )

        if args.output_format == "json":
            output = {
                "video_id": video_id,
                "title": title,
                "url": args.url,
                "engine": engine_used,
                "transcript": transcript,
                "char_count": len(transcript),
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(transcript)

    except EngineSelectionRequired as e:
        print(json.dumps(e.available_engines), file=sys.stderr)
        sys.exit(2)
    except MissingDependencyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired as e:
        print(f"Error: Command timed out after {e.timeout}s: {e.cmd}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
