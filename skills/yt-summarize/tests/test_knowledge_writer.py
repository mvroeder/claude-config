"""Tests for knowledge base writing (save_learnings)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-summarize")


class TestSaveLearnings(unittest.TestCase):
    def test_saves_json_and_md(self):
        summary = """## Key Learnings
- Test learning

```json
{
  "tags": ["testing", "python"],
  "learnings": [
    {
      "principle": "Always write tests",
      "details": "Tests catch bugs early",
      "actionable": "Write tests before code",
      "tags": ["testing"]
    }
  ]
}
```

More notes here."""

        with tempfile.TemporaryDirectory() as tmpdir:
            result = yt.save_learnings(
                summary_text=summary,
                title="Test Video",
                url="https://youtube.com/watch?v=abc12345678",
                video_id="abc12345678",
                knowledge_dir=tmpdir,
            )

            self.assertIsNotNone(result)
            json_path, md_path = result

            self.assertTrue(os.path.isfile(json_path))
            self.assertTrue(os.path.isfile(md_path))

            # Verify JSON content
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["source"], "youtube")
            self.assertEqual(data["video_id"], "abc12345678")
            self.assertEqual(data["title"], "Test Video")
            self.assertEqual(data["tags"], ["testing", "python"])
            self.assertEqual(len(data["learnings"]), 1)
            self.assertEqual(data["learnings"][0]["principle"], "Always write tests")

            # Verify MD content
            with open(md_path, encoding="utf-8") as f:
                md_content = f.read()
            self.assertIn("# Test Video", md_content)
            self.assertIn("Key Learnings", md_content)
            # JSON block should be stripped from markdown
            self.assertNotIn("```json", md_content)

    def test_creates_yt_learnings_dir(self):
        summary = '```json\n{"tags": [], "learnings": []}\n```'
        with tempfile.TemporaryDirectory() as tmpdir:
            yt.save_learnings(
                summary, "Test", "https://youtube.com/watch?v=abc12345678",
                "abc12345678", tmpdir,
            )
            self.assertTrue(os.path.isdir(os.path.join(tmpdir, "yt-learnings")))

    def test_returns_none_for_no_json(self):
        result = yt.save_learnings(
            "No JSON here", "Test", "https://youtube.com/watch?v=abc12345678",
            "abc12345678", "/tmp/test",
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
