"""faster-whisper transcription engine."""
import time
from pathlib import Path
import click
from casts_down.transcribe.engine import Segment, TranscribeEngine


class FasterWhisperEngine(TranscribeEngine):
    def __init__(self, model: str = "small"):
        self._model_name = model
        self._model = None
        self._device = None
        self._compute_type = None

    def _load_model(self, device: str | None = None):
        """Load model with specified device."""
        from faster_whisper import WhisperModel

        t0 = time.monotonic()
        if device:
            self._model = WhisperModel(self._model_name, device=device)
            self._device = device
        else:
            self._model = WhisperModel(self._model_name)
            self._device = "auto"
        elapsed = time.monotonic() - t0
        click.echo(f"[*] Model '{self._model_name}' loaded on {self._device} ({elapsed:.1f}s)")

    def _ensure_model(self):
        """Lazy load model: try cuda -> fallback cpu."""
        if self._model is not None:
            return

        # Try CUDA first
        try:
            self._load_model("cuda")
            _ = self._model.model  # force CUDA lib check
            click.echo(f"[*] Transcription engine: faster-whisper (cuda)")
            return
        except Exception:
            pass

        # Fallback to CPU
        self._load_model("cpu")
        click.echo(f"[*] Transcription engine: faster-whisper (cpu)")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        self._ensure_model()

        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        click.echo(f"[*] Transcribing: {audio_path.name} ({file_size_mb:.1f} MB)")

        try:
            segments = self._do_transcribe(audio_path, language)
        except RuntimeError as e:
            if "libcublas" in str(e) or "CUDA" in str(e) or "cuda" in str(e):
                click.echo(f"[!] CUDA error: {e}")
                click.echo("[*] Falling back to CPU...")
                self._load_model("cpu")
                segments = self._do_transcribe(audio_path, language)
            else:
                raise

        return segments

    def _do_transcribe(self, audio_path: Path, language: str | None) -> list[Segment]:
        t0 = time.monotonic()
        segments_iter, info = self._model.transcribe(
            str(audio_path), language=language, word_timestamps=False,
        )
        results = [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments_iter]
        elapsed = time.monotonic() - t0

        # Observability: audio duration, segments, speed
        audio_duration = info.duration
        audio_mins = int(audio_duration // 60)
        audio_secs = int(audio_duration % 60)
        speed_ratio = audio_duration / elapsed if elapsed > 0 else 0

        click.echo(
            f"[*] Done: {len(results)} segments, "
            f"audio {audio_mins}m{audio_secs:02d}s, "
            f"took {elapsed:.1f}s ({speed_ratio:.1f}x realtime), "
            f"lang={info.language} prob={info.language_probability:.2f}"
        )
        return results
