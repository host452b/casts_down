"""Tests for CLI command routing and arguments."""
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from casts_down.cli import main, check_system_deps

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

    def test_version_matches_pyproject(self):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        from casts_down import __version__
        with open("pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        assert pyproject["project"]["version"] == __version__

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


class TestURLValidation:
    def test_rejects_file_scheme(self, runner):
        result = runner.invoke(main, ["file:///etc/passwd"])
        assert result.exit_code != 0
        assert "http" in result.output.lower() or "https" in result.output.lower()

    def test_rejects_no_scheme(self, runner):
        result = runner.invoke(main, ["/etc/passwd"])
        assert result.exit_code != 0

    def test_accepts_https(self, runner):
        with patch("casts_down.cli._download_podcast", return_value=[]):
            result = runner.invoke(main, ["--no-transcribe", "https://example.com/feed.rss"])
        assert result.exit_code == 0

    def test_accepts_http(self, runner):
        with patch("casts_down.cli._download_podcast", return_value=[]):
            result = runner.invoke(main, ["--no-transcribe", "http://example.com/feed.rss"])
        assert result.exit_code == 0

class TestOptionValidation:
    def test_concurrent_zero_rejected(self, runner):
        result = runner.invoke(main, ["--concurrent", "0", "https://example.com/feed.rss"])
        assert result.exit_code != 0

    def test_concurrent_negative_rejected(self, runner):
        result = runner.invoke(main, ["-c", "-1", "https://example.com/feed.rss"])
        assert result.exit_code != 0

    def test_latest_zero_rejected(self, runner):
        result = runner.invoke(main, ["--latest", "0", "https://example.com/feed.rss"])
        assert result.exit_code != 0

    def test_latest_negative_rejected(self, runner):
        result = runner.invoke(main, ["-l", "-1", "https://example.com/feed.rss"])
        assert result.exit_code != 0


class TestCheckSystemDeps:
    """Unit tests for check_system_deps()."""

    def test_no_warning_when_ffmpeg_present(self, runner, capsys):
        with patch("casts_down.cli.shutil.which", return_value="/usr/local/bin/ffmpeg"):
            check_system_deps()
        captured = capsys.readouterr()
        assert "ffmpeg" not in captured.out

    def test_warning_when_ffmpeg_missing_macos(self, runner, capsys):
        with patch("casts_down.cli.shutil.which", return_value=None), \
             patch("casts_down.cli.platform.system", return_value="Darwin"):
            check_system_deps()
        captured = capsys.readouterr()
        assert "ffmpeg" in captured.out
        assert "brew install ffmpeg" in captured.out

    def test_warning_when_ffmpeg_missing_linux_apt(self, capsys):
        def fake_which(name):
            if name == "ffmpeg":
                return None
            if name == "apt":
                return "/usr/bin/apt"
            return None
        with patch("casts_down.cli.shutil.which", side_effect=fake_which), \
             patch("casts_down.cli.platform.system", return_value="Linux"):
            check_system_deps()
        captured = capsys.readouterr()
        assert "sudo apt install ffmpeg" in captured.out

    def test_warning_when_ffmpeg_missing_linux_dnf(self, capsys):
        def fake_which(name):
            if name == "ffmpeg":
                return None
            if name == "apt":
                return None
            if name == "dnf":
                return "/usr/bin/dnf"
            return None
        with patch("casts_down.cli.shutil.which", side_effect=fake_which), \
             patch("casts_down.cli.platform.system", return_value="Linux"):
            check_system_deps()
        captured = capsys.readouterr()
        assert "sudo dnf install ffmpeg" in captured.out

    def test_warning_shown_in_cli_output(self, runner):
        with patch("casts_down.cli.shutil.which", return_value=None), \
             patch("casts_down.cli.platform.system", return_value="Darwin"), \
             patch("casts_down.cli._download_podcast", return_value=[]):
            result = runner.invoke(main, ["--no-transcribe", "https://example.com/feed.rss"])
        assert "ffmpeg" in result.output
        assert "brew install ffmpeg" in result.output


class TestSetupTranscribe:
    def test_setup_help(self, runner):
        result = runner.invoke(main, ["setup-transcribe", "--help"])
        assert result.exit_code == 0

    def test_setup_runs_without_error(self, runner):
        result = runner.invoke(main, ["setup-transcribe"], input="y\n")
        assert result.exit_code == 0
        assert "Detecting environment" in result.output

    def test_backend_option_passed_through(self, runner):
        with patch("casts_down.transcribe.installer.run_setup") as mock_setup:
            result = runner.invoke(main, ["setup-transcribe", "--backend", "faster-whisper"])
        mock_setup.assert_called_once_with(backend="faster-whisper")
