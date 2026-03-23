#!/usr/bin/env python3
"""Summarize YouTube videos using yt-transcribe + Claude API.

Transcription is delegated to yt-transcribe (subprocess call).
Supports multiple summary modes: kurz, standard (default), learn.
Supports playlist URLs — processes all videos sequentially.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None


# ── Custom Exceptions ──


class MissingDependencyError(Exception):
    """Raised when a required dependency is not installed."""


class ConfigError(Exception):
    """Raised when a required configuration (e.g. API key) is missing."""


class EngineSelectionRequired(Exception):
    """Raised when yt-transcribe exits with code 2 (engine choice needed)."""

    def __init__(self, available_engines: dict[str, str]):
        self.available_engines = available_engines
        super().__init__(
            f"Engine selection required. Available: {json.dumps(available_engines)}"
        )


# ── Constants ──

SUBPROCESS_TIMEOUT_TRANSCRIBE = 900  # 15 min for full transcription
SUBPROCESS_TIMEOUT_PLAYLIST = 60

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


# ── Transcription via subprocess ──


def _find_yt_transcribe_script() -> str:
    """Locate the yt-transcribe.py script."""
    # Sibling skill in the same skills directory
    this_skill = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", ""))
    if this_skill.is_dir():
        candidate = this_skill.parent / "yt-transcribe" / "scripts" / "yt-transcribe.py"
        if candidate.is_file():
            return str(candidate)

    # Fallback: default skill location
    default = Path.home() / ".claude" / "skills" / "yt-transcribe" / "scripts" / "yt-transcribe.py"
    if default.is_file():
        return str(default)

    raise MissingDependencyError(
        "yt-transcribe skill not found. Install it alongside yt-summarize."
    )


def transcribe_video(url: str, engine: str, languages: str) -> tuple[str, str, str]:
    """Call yt-transcribe as subprocess and return (transcript, title, video_id).

    Raises EngineSelectionRequired if yt-transcribe exits with code 2.
    """
    script = _find_yt_transcribe_script()
    cmd = [
        sys.executable, script, url,
        "--engine", engine,
        "--lang", languages,
        "--format", "json",
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=SUBPROCESS_TIMEOUT_TRANSCRIBE,
    )

    if result.returncode == 2:
        # Engine selection required — parse available engines from stderr
        try:
            available = json.loads(result.stderr.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            available = {}
        raise EngineSelectionRequired(available)

    if result.returncode != 0:
        error_msg = result.stderr.strip() or "unknown error"
        raise RuntimeError(f"yt-transcribe failed: {error_msg}")

    data = json.loads(result.stdout)
    return data["transcript"], data["title"], data["video_id"]


# ── Playlist support ──


def is_playlist_url(url: str) -> bool:
    """Check if the URL points to a YouTube playlist."""
    return "list=" in url or "/playlist?" in url


def extract_playlist_videos(url: str) -> list[dict[str, str]]:
    """Extract video URLs and titles from a YouTube playlist using yt-dlp."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s",
        "--no-warnings",
        url,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_PLAYLIST
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to extract playlist: {result.stderr.strip() or 'unknown error'}"
        )

    videos = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        video_id = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else "Unknown Title"
        if video_id and len(video_id) == 11:
            videos.append({
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": title,
            })

    if not videos:
        raise RuntimeError("Playlist contains no videos or could not be parsed.")

    return videos


# ── Interest and skill loading ──


def load_interests(interests_path: str | None) -> str | None:
    """Load the user's INTERESTS.md file if it exists."""
    if interests_path and os.path.isfile(interests_path):
        with open(interests_path, encoding="utf-8") as f:
            return f.read().strip()
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


# ── Prompt building ──


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


# ── Summarization ──


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


# ── Learn mode helpers ──


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

    md_content = re.sub(r"```json\s*\n.*?\n```", "", summary_text, flags=re.DOTALL).strip()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source: {url}  \n")
        f.write(f"Date: {today}\n\n")
        f.write(md_content)
        f.write("\n")

    return json_path, md_path


# ── Video processing ──


def _resolve_knowledge_dir(args) -> str:
    """Determine the knowledge base directory from args or env."""
    if args.knowledge_dir:
        return args.knowledge_dir
    config_repo = os.environ.get("CLAUDE_CONFIG_REPO")
    if config_repo:
        return os.path.join(config_repo, "knowledge")
    return os.path.expanduser("~/.claude/knowledge")


def _summarize_and_output(
    transcript: str, title: str, url: str, video_id: str,
    args, interests: str | None, skills_list: str | None,
) -> None:
    """Summarize transcript and output results."""
    print(f"Summarizing with {args.model} (mode: {args.mode})...")
    summary = summarize(
        transcript, title, args.summary_lang, args.model,
        mode=args.mode, interests=interests, skills_list=skills_list,
    )
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")
    print(summary)

    if args.save_learnings and args.mode == "learn":
        knowledge_dir = _resolve_knowledge_dir(args)
        result = save_learnings(summary, title, url, video_id, knowledge_dir)
        if result:
            json_path, md_path = result
            print(f"\nLearnings saved:")
            print(f"  JSON: {json_path}")
            print(f"  Markdown: {md_path}")


def _run_single_video(args) -> None:
    """Process a single video URL."""
    transcript, title, video_id = transcribe_video(
        args.url, args.engine, args.lang
    )

    if args.transcript_only:
        print(transcript)
        return

    interests = load_interests(args.interests)
    skills_list = scan_skills(None) if args.mode == "learn" else None
    _summarize_and_output(
        transcript, title, args.url, video_id, args, interests, skills_list
    )


def _run_playlist(args) -> None:
    """Process all videos in a YouTube playlist."""
    print("Extracting playlist videos...")
    videos = extract_playlist_videos(args.url)
    total = len(videos)
    print(f"Found {total} videos in playlist.\n")

    interests = load_interests(args.interests) if not args.transcript_only else None
    skills_list = scan_skills(None) if args.mode == "learn" and not args.transcript_only else None

    succeeded = 0
    failed = 0

    for i, video in enumerate(videos, 1):
        print(f"\n{'#' * 60}")
        print(f"  [{i}/{total}] {video['title']}")
        print(f"  {video['url']}")
        print(f"{'#' * 60}\n")

        try:
            transcript, title, video_id = transcribe_video(
                video["url"], args.engine, args.lang
            )

            if args.transcript_only:
                print(transcript)
            else:
                _summarize_and_output(
                    transcript, title, video["url"], video_id,
                    args, interests, skills_list,
                )
            succeeded += 1
        except Exception as e:
            print(f"\nError processing video {video['id']}: {e}", file=sys.stderr)
            failed += 1
            continue

    print(f"\n{'=' * 60}")
    print(f"  Playlist complete: {succeeded} succeeded, {failed} failed out of {total}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="Summarize YouTube videos with Claude (transcription via yt-transcribe)"
    )
    parser.add_argument("url", help="YouTube video URL, video ID, or playlist URL")
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
        default="standard",
        help="Summary mode: kurz (brief), standard (default, detailed), learn (extract learnings)",
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
        help="Transcription engine passed to yt-transcribe (default: auto)",
    )
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
        help="Knowledge base directory (default: $CLAUDE_CONFIG_REPO/knowledge)",
    )
    args = parser.parse_args()

    if args.whisper:
        args.engine = "whisper"

    try:
        if not args.transcript_only and not os.environ.get("ANTHROPIC_API_KEY"):
            raise ConfigError(
                "ANTHROPIC_API_KEY not set. Export it or add to .env: export ANTHROPIC_API_KEY=sk-ant-..."
            )

        if is_playlist_url(args.url):
            _run_playlist(args)
        else:
            _run_single_video(args)

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
