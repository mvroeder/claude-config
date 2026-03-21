#!/usr/bin/env python3
"""Transcribe and summarize YouTube videos using yt-dlp + Claude API.

Hybrid transcription: tries YouTube subtitles first, then offers interactive
choice between local Whisper, OpenAI Whisper API, or GPT-4o-Transcribe.

Supports multiple summary modes: kurz (default), standard, learn.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None

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

# ── Prompt Templates ──

PROMPTS = {
    "kurz": """Here is the transcript of a YouTube video titled "{title}".
Please provide a structured summary in {language}:

1. **Kernaussagen** — The 3-5 most important points
2. **Zusammenfassung** — A concise summary (max 300 words)
3. **Interessante Details** — Notable quotes, data points, or insights
4. **Fazit** — One-sentence takeaway

{interests_section}

Transcript:
{transcript}""",
    "standard": """Here is the transcript of a YouTube video titled "{title}".
Please provide a comprehensive, detailed summary in {language} (up to 2000 words):

1. **Kontext & Hintergrund** — What is this video about? Who is presenting? What is the broader context?
2. **Kernaussagen** — The 5-8 most important points, each explained in 2-3 sentences
3. **Detaillierte Zusammenfassung** — A thorough summary covering all major topics discussed (up to 1500 words). Structure with subheadings where appropriate.
4. **Zitate & Daten** — Notable direct quotes, statistics, data points, or concrete examples
5. **Interessante Details** — Subtle insights, surprising facts, or lesser-known information mentioned
6. **Kritische Einordnung** — Any limitations, biases, or missing perspectives
7. **Fazit & Bewertung** — Overall assessment and key takeaway

{interests_section}

Transcript:
{transcript}""",
    "learn": """Here is the transcript of a YouTube video titled "{title}".

Extract actionable learnings from this video. Respond in {language} with TWO sections:

## SECTION 1: MARKDOWN SUMMARY

Provide a human-readable learning summary:

1. **Key Learnings** — The most important principles, techniques, or insights (each as a clear, memorable statement)
2. **How to Apply** — Concrete, actionable steps to apply these learnings
3. **Mental Models** — Any frameworks, mental models, or thinking patterns introduced
4. **Connections** — How these learnings connect to broader topics

## SECTION 2: JSON DATA

After the markdown summary, output a JSON block wrapped in ```json fences with this exact structure:
```json
{{
  "tags": ["tag1", "tag2", "tag3"],
  "learnings": [
    {{
      "principle": "Clear, memorable statement of the learning",
      "details": "Supporting explanation and context",
      "actionable": "How to apply this concretely",
      "tags": ["relevant", "tags"]
    }}
  ]
}}
```

{interests_section}

{skills_section}

Transcript:
{transcript}""",
}

INTERESTS_SECTION_TEMPLATE = """IMPORTANT: The user has the following interest profile. Assess how relevant this video's content is to their interests and highlight the most relevant parts. If a topic falls under "Not Interested", de-prioritize it.

User Profile:
{interests}"""

SKILLS_SECTION_TEMPLATE = """The user has the following Claude Code skills installed. If any learnings from this video could improve these skills, note which skill and what could be improved:

Installed Skills:
{skills_list}"""


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

        print("Transcribing with Whisper (this may take a while)...")
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

        print(f"Transcribing with {model} API...")
        with open(audio_file, "rb") as af:
            response = client.audio.transcriptions.create(
                model=model,
                file=af,
                response_format="text",
            )

        # response is a string when response_format="text"
        return response.strip() if isinstance(response, str) else response.text.strip()


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
    available engines as JSON on stderr, using exit code 2. This allows
    SKILL.md to catch the error and use AskUserQuestion instead.
    """
    if not available:
        raise ConfigError(
            "No transcription engine available. Options:\n"
            "  - Install local Whisper: uv pip install openai-whisper\n"
            "  - Set OPENAI_API_KEY for API transcription: uv pip install openai"
        )

    if len(available) == 1:
        key = next(iter(available))
        print(f"Using {available[key]} (only available engine).")
        return key

    # Non-interactive mode: signal that engine selection is needed
    if not sys.stdin.isatty():
        raise EngineSelectionRequired(available)

    print("\nNo subtitles found. Choose a transcription engine:\n")
    keys = list(available.keys())
    for i, key in enumerate(keys, 1):
        print(f"  [{i}] {available[key]}")
    print()

    while True:
        try:
            choice = input(f"Enter choice (1-{len(keys)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {len(keys)}.")


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


def load_interests(interests_path: str | None) -> str | None:
    """Load the user's INTERESTS.md file if it exists."""
    if interests_path and os.path.isfile(interests_path):
        with open(interests_path, encoding="utf-8") as f:
            return f.read().strip()
    # Try default location
    default_path = os.path.expanduser("~/.claude/INTERESTS.md")
    if os.path.isfile(default_path):
        with open(default_path, encoding="utf-8") as f:
            return f.read().strip()
    return None


def scan_skills(skills_dir: str | None) -> str | None:
    """Scan installed skills and return a summary for the learn mode prompt."""
    if skills_dir is None:
        skills_dir = os.path.expanduser("~/.claude/skills")
    if not os.path.isdir(skills_dir):
        return None

    skills_info = []
    for skill_path in sorted(Path(skills_dir).iterdir()):
        skill_md = skill_path / "SKILL.md"
        if not skill_md.is_file():
            continue
        content = skill_md.read_text(encoding="utf-8")
        # Extract name and description from YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            continue
        frontmatter = frontmatter_match.group(1)
        name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip().strip("\"'")
            desc = desc_match.group(1).strip().strip("\"'") if desc_match else ""
            skills_info.append(f"- **{name}**: {desc}")

    return "\n".join(skills_info) if skills_info else None


def build_prompt(
    transcript: str,
    title: str,
    language: str,
    mode: str,
    interests: str | None,
    skills_list: str | None,
) -> str:
    """Build the summarization prompt for the given mode."""
    template = PROMPTS[mode]

    interests_section = ""
    if interests:
        interests_section = INTERESTS_SECTION_TEMPLATE.format(interests=interests)

    skills_section = ""
    if mode == "learn" and skills_list:
        skills_section = SKILLS_SECTION_TEMPLATE.format(skills_list=skills_list)

    return template.format(
        title=title,
        language=language,
        transcript=transcript,
        interests_section=interests_section,
        skills_section=skills_section,
    )


def summarize(
    transcript: str,
    title: str,
    language: str,
    model: str,
    mode: str = "kurz",
    interests: str | None = None,
    skills_list: str | None = None,
) -> str:
    """Send the transcript to Claude for summarization."""
    if anthropic is None:
        raise MissingDependencyError(
            "Missing dependency: anthropic. Install with: uv pip install anthropic"
        )

    client = anthropic.Anthropic()
    prompt = build_prompt(transcript, title, language, mode, interests, skills_list)

    max_tokens = 4096 if mode in ("standard", "learn") else 2048

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def extract_learn_json(summary_text: str) -> dict | None:
    """Extract the JSON block from learn mode output."""
    match = re.search(r"```json\s*\n(.*?)\n```", summary_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def save_learnings(
    summary_text: str,
    title: str,
    url: str,
    video_id: str,
    knowledge_dir: str,
) -> tuple[str, str] | None:
    """Save learn mode output as JSON + Markdown files. Returns (json_path, md_path) or None."""
    learn_data = extract_learn_json(summary_text)
    if learn_data is None:
        print("Warning: Could not extract JSON from learn mode output.", file=sys.stderr)
        return None

    yt_dir = os.path.join(knowledge_dir, "yt-learnings")
    os.makedirs(yt_dir, exist_ok=True)

    today = date.today().isoformat()
    base_name = f"{today}_{video_id}"
    json_path = os.path.join(yt_dir, f"{base_name}.json")
    md_path = os.path.join(yt_dir, f"{base_name}.md")

    # Build full JSON record
    record = {
        "source": "youtube",
        "video_id": video_id,
        "title": title,
        "url": url,
        "date_extracted": today,
        "mode": "learn",
        **learn_data,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # Extract markdown portion (everything before the JSON block)
    md_content = re.sub(r"```json\s*\n.*?\n```", "", summary_text, flags=re.DOTALL).strip()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source: {url}  \n")
        f.write(f"Date: {today}\n\n")
        f.write(md_content)
        f.write("\n")

    return json_path, md_path


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
        "--mode",
        choices=["kurz", "standard", "learn"],
        default="kurz",
        help="Summary mode: kurz (default), standard (detailed), learn (extract learnings)",
    )
    parser.add_argument(
        "--transcript-only",
        action="store_true",
        help="Only output the transcript, skip summarization",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "whisper", "whisper-api", "gpt4o-transcribe"],
        default="auto",
        help="Transcription engine (default: auto — subtitles first, then interactive choice)",
    )
    # Keep --whisper as shortcut for backwards compatibility
    parser.add_argument(
        "--whisper",
        action="store_true",
        help="Shortcut for --engine whisper",
    )
    parser.add_argument(
        "--interests",
        default=None,
        help="Path to INTERESTS.md file (default: ~/.claude/INTERESTS.md)",
    )
    parser.add_argument(
        "--save-learnings",
        action="store_true",
        help="Save learn mode output to knowledge base (learn mode only)",
    )
    parser.add_argument(
        "--knowledge-dir",
        default=None,
        help="Knowledge base directory (default: ~/claude-config/knowledge or $CLAUDE_CONFIG_REPO/knowledge)",
    )
    args = parser.parse_args()

    # --whisper flag overrides --engine
    if args.whisper:
        args.engine = "whisper"

    try:
        # Check yt-dlp is installed
        if not shutil.which("yt-dlp"):
            raise MissingDependencyError(
                "yt-dlp not found. Install with: uv pip install yt-dlp"
            )

        # Check API key unless transcript-only
        if not args.transcript_only and not os.environ.get("ANTHROPIC_API_KEY"):
            raise ConfigError(
                "ANTHROPIC_API_KEY not set. Export it or add to .env: export ANTHROPIC_API_KEY=sk-ant-..."
            )

        languages = [lang.strip() for lang in args.lang.split(",")]

        print("Fetching video title...")
        title = get_video_title(args.url)
        print(f"Title: {title}\n")

        # Transcription logic
        transcript = None

        if args.engine != "auto":
            engine_name = ENGINES.get(args.engine, args.engine)
            print(f"Transcribing with {engine_name}...")
            transcript = transcribe_with_engine(args.url, args.engine)
            print(f"Transcript ({engine_name}): {len(transcript)} characters\n")
        else:
            print(f"Extracting subtitles ({', '.join(languages)})...")
            transcript = fetch_transcript_subtitles(args.url, languages)
            if transcript:
                print(f"Transcript (subtitles): {len(transcript)} characters\n")
            else:
                available = get_available_engines()
                engine = prompt_engine_choice(available)
                transcript = transcribe_with_engine(args.url, engine)
                engine_name = ENGINES.get(engine, engine)
                print(f"Transcript ({engine_name}): {len(transcript)} characters\n")

        if args.transcript_only:
            print(transcript)
            return

        # Load interests profile
        interests = load_interests(args.interests)

        # Scan skills for learn mode
        skills_list = None
        if args.mode == "learn":
            skills_list = scan_skills(None)

        print(f"Summarizing with {args.model} (mode: {args.mode})...")
        summary = summarize(
            transcript, title, args.summary_lang, args.model,
            mode=args.mode, interests=interests, skills_list=skills_list,
        )
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")
        print(summary)

        # Save learnings if requested
        if args.save_learnings and args.mode == "learn":
            video_id = extract_video_id(args.url)
            knowledge_dir = args.knowledge_dir
            if not knowledge_dir:
                config_repo = os.environ.get("CLAUDE_CONFIG_REPO")
                if config_repo:
                    knowledge_dir = os.path.join(config_repo, "knowledge")
                else:
                    knowledge_dir = os.path.expanduser("~/.claude/knowledge")

            result = save_learnings(summary, title, args.url, video_id, knowledge_dir)
            if result:
                json_path, md_path = result
                print(f"\nLearnings saved:")
                print(f"  JSON: {json_path}")
                print(f"  Markdown: {md_path}")

    except EngineSelectionRequired as e:
        # Exit code 2 signals SKILL.md to use AskUserQuestion
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
