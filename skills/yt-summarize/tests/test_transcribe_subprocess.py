"""Tests for subprocess-based transcription in yt-summarize."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-summarize")


class TestTranscribeVideo(unittest.TestCase):
    """Test the subprocess-based transcribe_video function."""

    @patch.object(yt, "_find_yt_transcribe_script", return_value="/fake/yt-transcribe.py")
    @patch("subprocess.run")
    def test_success_returns_transcript_title_id(self, mock_run, mock_find):
        json_output = json.dumps({
            "video_id": "dQw4w9WgXcQ",
            "title": "Test Video",
            "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "engine": "subtitles",
            "transcript": "Hello world transcript",
            "char_count": 22,
        })
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json_output, stderr=""
        )

        transcript, title, video_id = yt.transcribe_video(
            "https://youtube.com/watch?v=dQw4w9WgXcQ", "auto", "de,en"
        )
        self.assertEqual(transcript, "Hello world transcript")
        self.assertEqual(title, "Test Video")
        self.assertEqual(video_id, "dQw4w9WgXcQ")

    @patch.object(yt, "_find_yt_transcribe_script", return_value="/fake/yt-transcribe.py")
    @patch("subprocess.run")
    def test_exit_code_2_raises_engine_selection(self, mock_run, mock_find):
        engines = {"whisper": "Whisper (local)"}
        mock_run.return_value = MagicMock(
            returncode=2, stdout="", stderr=json.dumps(engines)
        )

        with self.assertRaises(yt.EngineSelectionRequired) as ctx:
            yt.transcribe_video("https://youtube.com/watch?v=test", "auto", "de,en")
        self.assertEqual(ctx.exception.available_engines, engines)

    @patch.object(yt, "_find_yt_transcribe_script", return_value="/fake/yt-transcribe.py")
    @patch("subprocess.run")
    def test_exit_code_1_raises_runtime_error(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error: yt-dlp not found"
        )

        with self.assertRaises(RuntimeError) as ctx:
            yt.transcribe_video("https://youtube.com/watch?v=test", "auto", "de,en")
        self.assertIn("yt-dlp not found", str(ctx.exception))


class TestFindYtTranscribeScript(unittest.TestCase):
    """Test script discovery logic."""

    @patch.dict("os.environ", {"CLAUDE_PLUGIN_ROOT": ""})
    @patch("pathlib.Path.is_file", return_value=False)
    def test_raises_when_not_found(self, mock_is_file):
        with self.assertRaises(yt.MissingDependencyError):
            yt._find_yt_transcribe_script()


if __name__ == "__main__":
    unittest.main()
