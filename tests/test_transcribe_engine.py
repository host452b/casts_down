"""Tests for engine detection and fallback logic."""
from unittest.mock import patch, MagicMock
import importlib
import pytest

from casts_down.transcribe.engine import TranscribeEngine, Segment


class TestTranscribeEngineABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            TranscribeEngine()

    def test_concrete_engine_must_implement_transcribe(self):
        class BadEngine(TranscribeEngine):
            pass
        with pytest.raises(TypeError):
            BadEngine()

    def test_concrete_engine_works(self):
        class GoodEngine(TranscribeEngine):
            def transcribe(self, audio_path, language=None):
                return [Segment(0.0, 1.0, "test")]
        engine = GoodEngine()
        assert len(engine.transcribe("dummy")) == 1


class TestDetectEngine:
    def test_mac_arm64_prefers_mlx(self):
        with patch("casts_down.transcribe.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            mock_platform.machine.return_value = "arm64"
            mock_mlx = MagicMock()
            with patch.dict("sys.modules", {"mlx_whisper": mock_mlx}):
                import casts_down.transcribe as t
                importlib.reload(t)
                engine = t.detect_engine(model="small")
                assert type(engine).__name__ == "MLXWhisperEngine"

    def test_mac_arm64_falls_back_to_faster_whisper(self):
        with patch("casts_down.transcribe.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            mock_platform.machine.return_value = "arm64"
            mock_fw = MagicMock()
            with patch.dict("sys.modules", {"mlx_whisper": None, "faster_whisper": mock_fw}):
                import casts_down.transcribe as t
                importlib.reload(t)
                engine = t.detect_engine(model="small")
                assert type(engine).__name__ == "FasterWhisperEngine"

    def test_linux_uses_faster_whisper(self):
        with patch("casts_down.transcribe.platform") as mock_platform:
            mock_platform.system.return_value = "Linux"
            mock_platform.machine.return_value = "x86_64"
            mock_fw = MagicMock()
            with patch.dict("sys.modules", {"faster_whisper": mock_fw, "mlx_whisper": None}):
                import casts_down.transcribe as t
                importlib.reload(t)
                engine = t.detect_engine(model="small")
                assert type(engine).__name__ == "FasterWhisperEngine"

    def test_no_engine_raises_error(self):
        with patch("casts_down.transcribe.platform") as mock_platform:
            mock_platform.system.return_value = "Linux"
            mock_platform.machine.return_value = "x86_64"
            with patch.dict("sys.modules", {"faster_whisper": None, "mlx_whisper": None}):
                import casts_down.transcribe as t
                importlib.reload(t)
                with pytest.raises(RuntimeError, match="setup-transcribe"):
                    t.detect_engine(model="small")
