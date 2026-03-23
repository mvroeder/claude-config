"""Tests for vtt_to_plain_text function."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-transcribe")


class TestVttToPlainText(unittest.TestCase):
    def _write_vtt(self, content: str) -> str:
        """Write VTT content to a temp file and return the path."""
        fd, path = tempfile.mkstemp(suffix=".vtt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(lambda: os.unlink(path))
        return path

    def test_basic_vtt(self):
        vtt = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000
Hello world

00:00:02.000 --> 00:00:04.000
This is a test
"""
        result = yt.vtt_to_plain_text(self._write_vtt(vtt))
        self.assertEqual(result, "Hello world This is a test")

    def test_deduplication(self):
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world

00:00:01.000 --> 00:00:03.000
Hello world

00:00:02.000 --> 00:00:04.000
New line
"""
        result = yt.vtt_to_plain_text(self._write_vtt(vtt))
        self.assertEqual(result, "Hello world New line")

    def test_html_tag_removal(self):
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
<c>Hello</c> <b>world</b>
"""
        result = yt.vtt_to_plain_text(self._write_vtt(vtt))
        self.assertEqual(result, "Hello world")

    def test_empty_vtt(self):
        vtt = """WEBVTT
Kind: captions
Language: en
"""
        result = yt.vtt_to_plain_text(self._write_vtt(vtt))
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
