"""faster-whisper transcription engine."""
from pathlib import Path
import click
from casts_down.transcribe.engine import Segment, TranscribeEngine


class FasterWhisperEngine(TranscribeEngine):
    def __init__(self, model: str = "small"):
        from faster_whisper import WhisperModel

        # Try CUDA first, fallback to CPU if GPU libs are missing
        try:
            self.model = WhisperModel(model, device="cuda")
            click.echo("[*] Transcription engine: faster-whisper (cuda)")
        except Exception:
            try:
                self.model = WhisperModel(model, device="cpu")
                click.echo("[*] Transcription engine: faster-whisper (cpu)")
            except Exception:
                # Let faster-whisper auto-detect
                self.model = WhisperModel(model)
                click.echo("[*] Transcription engine: faster-whisper (auto)")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        segments_iter, _info = self.model.transcribe(
            str(audio_path), language=language, word_timestamps=False,
        )
        return [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments_iter]
