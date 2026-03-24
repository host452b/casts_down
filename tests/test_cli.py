"""Tests for CLI command routing and arguments."""
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from casts_down.cli import main

@pytest.fixture
def runner():
    return CliRunner()

class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Casts Down" in result.output

    def test_no_args_shows_help(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code == 0

class TestTranscribeFlag:
    @patch("casts_down.cli._run_transcription")
    @patch("casts_down.cli._download_podcast")
    def test_transcribe_flag_triggers_transcription(self, mock_dl, mock_tr, runner):
        fake_path = MagicMock()
        mock_dl.return_value = [fake_path]
        # Options must precede the URL positional argument in Click's parsing
        result = runner.invoke(main, ["--transcribe", "https://example.com/feed.rss"])
        mock_tr.assert_called_once()

    @patch("casts_down.cli._download_podcast")
    def test_no_transcribe_by_default(self, mock_dl, runner):
        mock_dl.return_value = []
        with patch("casts_down.cli._run_transcription") as mock_tr:
            result = runner.invoke(main, ["https://example.com/feed.rss"])
            mock_tr.assert_not_called()

class TestTranscribeSubcommand:
    def test_transcribe_help(self, runner):
        result = runner.invoke(main, ["transcribe", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output

    def test_transcribe_single_file(self, runner, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.touch()
        with patch("casts_down.cli._run_transcription") as mock_run:
            result = runner.invoke(main, ["transcribe", str(audio)])
        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_transcribe_no_files_exits_nonzero(self, runner):
        result = runner.invoke(main, ["transcribe"])
        assert result.exit_code != 0

class TestSetupTranscribe:
    def test_setup_help(self, runner):
        result = runner.invoke(main, ["setup-transcribe", "--help"])
        assert result.exit_code == 0

    def test_setup_runs_without_error(self, runner):
        result = runner.invoke(main, ["setup-transcribe"])
        assert result.exit_code == 0
        assert "Detecting environment" in result.output
