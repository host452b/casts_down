"""faster-whisper transcription engine."""
from pathlib import Path
import click
from casts_down.transcribe.engine import Segment, TranscribeEngine


class FasterWhisperEngine(TranscribeEngine):
    def __init__(self, model: str = "small"):
        self._model_name = model
        self._model = None
        self._device = None

    def _load_model(self, device: str | None = None):
        """Load model with specified device, or auto-detect."""
        from faster_whisper import WhisperModel

        if device:
            self._model = WhisperModel(self._model_name, device=device)
            self._device = device
        else:
            self._model = WhisperModel(self._model_name)
            self._device = "auto"

    def _ensure_model(self):
        """Lazy load model: try cuda -> fallback cpu."""
        if self._model is not None:
            return

        # Try CUDA first
        try:
            self._load_model("cuda")
            # Force a check by accessing compute type — some CUDA errors are deferred
            _ = self._model.model
            click.echo(f"[*] Transcription engine: faster-whisper (cuda)")
            return
        except Exception:
            pass

        # Fallback to CPU
        self._load_model("cpu")
        click.echo(f"[*] Transcription engine: faster-whisper (cpu)")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        self._ensure_model()

        try:
            segments_iter, _info = self._model.transcribe(
                str(audio_path), language=language, word_timestamps=False,
            )
            return [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments_iter]
        except RuntimeError as e:
            if "libcublas" in str(e) or "CUDA" in str(e) or "cuda" in str(e):
                # CUDA failed at inference time — reload with CPU and retry
                click.echo(f"[!] CUDA error: {e}")
                click.echo("[*] Falling back to CPU...")
                self._load_model("cpu")
                segments_iter, _info = self._model.transcribe(
                    str(audio_path), language=language, word_timestamps=False,
                )
                return [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments_iter]
            raise
