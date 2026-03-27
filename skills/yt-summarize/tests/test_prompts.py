"""Tests for prompt building and mode selection."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-summarize")


class TestBuildPrompt(unittest.TestCase):
    def test_kurz_mode_contains_kernaussagen(self):
        prompt = yt.build_prompt(
            transcript="test transcript",
            title="Test Video",
            language="Deutsch",
            mode="kurz",
            interests=None,
            skills_list=None,
        )
        self.assertIn("Kernaussagen", prompt)
        self.assertIn("max 300 words", prompt)
        self.assertIn("test transcript", prompt)
        self.assertIn("Test Video", prompt)

    def test_standard_mode_contains_2000_words(self):
        prompt = yt.build_prompt(
            transcript="test transcript",
            title="Test Video",
            language="Deutsch",
            mode="standard",
            interests=None,
            skills_list=None,
        )
        self.assertIn("2000", prompt)
        self.assertIn("Kritische Einordnung", prompt)

    def test_learn_mode_contains_json_structure(self):
        prompt = yt.build_prompt(
            transcript="test transcript",
            title="Test Video",
            language="Deutsch",
            mode="learn",
            interests=None,
            skills_list=None,
        )
        self.assertIn("JSON", prompt)
        self.assertIn("principle", prompt)
        self.assertIn("actionable", prompt)

    def test_interests_injected_when_provided(self):
        prompt = yt.build_prompt(
            transcript="test",
            title="Test",
            language="Deutsch",
            mode="kurz",
            interests="## Topics of Interest\n- AI Agents",
            skills_list=None,
        )
        self.assertIn("AI Agents", prompt)
        self.assertIn("interest profile", prompt.lower())

    def test_no_interests_section_when_none(self):
        prompt = yt.build_prompt(
            transcript="test",
            title="Test",
            language="Deutsch",
            mode="kurz",
            interests=None,
            skills_list=None,
        )
        self.assertNotIn("interest profile", prompt.lower())

    def test_skills_only_in_learn_mode(self):
        skills = "- **last30days**: Research topics"
        prompt_learn = yt.build_prompt(
            transcript="test", title="Test", language="Deutsch",
            mode="learn", interests=None, skills_list=skills,
        )
        prompt_kurz = yt.build_prompt(
            transcript="test", title="Test", language="Deutsch",
            mode="kurz", interests=None, skills_list=skills,
        )
        self.assertIn("last30days", prompt_learn)
        self.assertNotIn("last30days", prompt_kurz)


class TestExtractLearnJson(unittest.TestCase):
    def test_extracts_valid_json(self):
        text = """Some markdown here.

```json
{
  "tags": ["ai", "testing"],
  "learnings": [{"principle": "test", "details": "d", "actionable": "a", "tags": ["t"]}]
}
```

More text."""
        result = yt.extract_learn_json(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["tags"], ["ai", "testing"])
        self.assertEqual(len(result["learnings"]), 1)

    def test_returns_none_for_no_json(self):
        self.assertIsNone(yt.extract_learn_json("No JSON here"))

    def test_returns_none_for_invalid_json(self):
        text = '```json\n{invalid json}\n```'
        self.assertIsNone(yt.extract_learn_json(text))


if __name__ == "__main__":
    unittest.main()
