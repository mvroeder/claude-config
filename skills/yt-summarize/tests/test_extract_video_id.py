"""Tests for extract_video_id — now lives in yt-transcribe.

These tests verify the function is available via yt-transcribe.
The yt-summarize skill no longer contains this function directly.
"""

import sys
import unittest
from pathlib import Path

# Import from yt-transcribe (sibling skill)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "yt-transcribe" / "scripts"))

from importlib import import_module

yt = import_module("yt-transcribe")


class TestExtractVideoId(unittest.TestCase):
    def test_standard_url(self):
        self.assertEqual(
            yt.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_short_url(self):
        self.assertEqual(
            yt.extract_video_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_bare_id(self):
        self.assertEqual(yt.extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            yt.extract_video_id("https://example.com/not-a-video")


if __name__ == "__main__":
    unittest.main()
