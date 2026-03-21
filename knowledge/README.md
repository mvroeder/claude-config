# Knowledge Base

Structured learnings extracted from various sources. Synced to `~/.claude/knowledge/` by `sync-skills.sh`.

## Structure

```
knowledge/
├── README.md
└── yt-learnings/          # Learnings from YouTube videos (via yt-summarize)
    ├── YYYY-MM-DD_<video-id>.json   # Structured data
    └── YYYY-MM-DD_<video-id>.md     # Human-readable summary
```

## JSON Format

```json
{
  "source": "youtube",
  "video_id": "abc123",
  "title": "Video Title",
  "url": "https://youtube.com/watch?v=abc123",
  "date_extracted": "2026-03-21",
  "mode": "learn",
  "tags": ["topic1", "topic2"],
  "learnings": [
    {
      "principle": "Clear statement of the learning",
      "details": "Supporting context and explanation",
      "actionable": "How to apply this concretely",
      "tags": ["relevant", "tags"]
    }
  ],
  "skill_matches": [
    {
      "skill": "skill-name",
      "relevance": "high|medium|low",
      "suggestion": "What could be improved"
    }
  ]
}
```

## Usage

- **By humans**: Read the `.md` files for quick learning summaries
- **By agents**: Parse `.json` files for structured data, tags, and skill matching
- **By skills**: Skills can read `~/.claude/knowledge/` to build on previous learnings
