"""Tests for output format handling."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-transcribe")


class TestTranscribeVideo(unittest.TestCase):
    """Test the transcribe_video function returns (transcript, engine_used)."""

    @patch.object(yt, "fetch_transcript_subtitles", return_value="Hello world transcript")
    def test_auto_with_subtitles(self, mock_subs):
        transcript, engine = yt.transcribe_video(
            "https://youtube.com/watch?v=test123test",
            engine="auto",
            languages=["de", "en"],
        )
        self.assertEqual(transcript, "Hello world transcript")
        self.assertEqual(engine, "subtitles")
        mock_subs.assert_called_once()

    @patch.object(yt, "fetch_transcript_subtitles", return_value=None)
    @patch.object(yt, "get_available_engines", return_value={"whisper": "Whisper (local)"})
    @patch.object(yt, "transcribe_with_engine", return_value="Whisper transcript")
    def test_auto_fallback_single_engine(self, mock_engine, mock_avail, mock_subs):
        transcript, engine = yt.transcribe_video(
            "https://youtube.com/watch?v=test123test",
            engine="auto",
            languages=["de", "en"],
        )
        self.assertEqual(transcript, "Whisper transcript")
        self.assertEqual(engine, "whisper")

    @patch.object(yt, "transcribe_with_engine", return_value="Direct transcript")
    def test_explicit_engine(self, mock_engine):
        transcript, engine = yt.transcribe_video(
            "https://youtube.com/watch?v=test123test",
            engine="whisper-api",
            languages=["de"],
        )
        self.assertEqual(transcript, "Direct transcript")
        self.assertEqual(engine, "whisper-api")
        mock_engine.assert_called_once_with("https://youtube.com/watch?v=test123test", "whisper-api")


class TestJsonOutput(unittest.TestCase):
    """Test that JSON output structure is correct."""

    def test_json_structure(self):
        """Verify expected keys in JSON output dict."""
        output = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "engine": "subtitles",
            "transcript": "Hello world",
            "char_count": 11,
        }
        parsed = json.loads(json.dumps(output))
        expected_keys = {"video_id", "title", "url", "engine", "transcript", "char_count"}
        self.assertEqual(set(parsed.keys()), expected_keys)
        self.assertEqual(parsed["char_count"], len(parsed["transcript"]))


if __name__ == "__main__":
    unittest.main()
