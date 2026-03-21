"""Tests for extract_video_id function."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-summarize")


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

    def test_url_with_params(self):
        self.assertEqual(
            yt.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42"),
            "dQw4w9WgXcQ",
        )

    def test_bare_id(self):
        self.assertEqual(yt.extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_embed_url(self):
        self.assertEqual(
            yt.extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            yt.extract_video_id("https://example.com/not-a-video")

    def test_invalid_short_string(self):
        with self.assertRaises(ValueError):
            yt.extract_video_id("abc")


if __name__ == "__main__":
    unittest.main()
