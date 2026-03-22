"""Tests for playlist detection and URL parsing."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from importlib import import_module

yt = import_module("yt-summarize")


class TestIsPlaylistUrl(unittest.TestCase):
    def test_standard_playlist(self):
        self.assertTrue(
            yt.is_playlist_url(
                "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
            )
        )

    def test_video_in_playlist(self):
        self.assertTrue(
            yt.is_playlist_url(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
            )
        )

    def test_single_video(self):
        self.assertFalse(
            yt.is_playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

    def test_short_url(self):
        self.assertFalse(yt.is_playlist_url("https://youtu.be/dQw4w9WgXcQ"))

    def test_bare_id(self):
        self.assertFalse(yt.is_playlist_url("dQw4w9WgXcQ"))


class TestExtractPlaylistVideos(unittest.TestCase):
    @patch("subprocess.run")
    def test_parses_yt_dlp_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="dQw4w9WgXcQ\tNever Gonna Give You Up\nabc12345678\tAnother Video\n",
            stderr="",
        )
        videos = yt.extract_playlist_videos("https://youtube.com/playlist?list=PLtest")
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0]["id"], "dQw4w9WgXcQ")
        self.assertEqual(videos[0]["title"], "Never Gonna Give You Up")
        self.assertEqual(
            videos[0]["url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertEqual(videos[1]["id"], "abc12345678")

    @patch("subprocess.run")
    def test_skips_invalid_ids(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="dQw4w9WgXcQ\tValid Video\nshort\tToo Short ID\n",
            stderr="",
        )
        videos = yt.extract_playlist_videos("https://youtube.com/playlist?list=PLtest")
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["id"], "dQw4w9WgXcQ")

    @patch("subprocess.run")
    def test_raises_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ERROR: playlist not found",
        )
        with self.assertRaises(RuntimeError):
            yt.extract_playlist_videos("https://youtube.com/playlist?list=PLbad")

    @patch("subprocess.run")
    def test_raises_on_empty_playlist(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="\n",
            stderr="",
        )
        with self.assertRaises(RuntimeError):
            yt.extract_playlist_videos("https://youtube.com/playlist?list=PLempty")


if __name__ == "__main__":
    unittest.main()
