"""faster-whisper transcription engine."""
from pathlib import Path
import click
from casts_down.transcribe.engine import Segment, TranscribeEngine

class FasterWhisperEngine(TranscribeEngine):
    def __init__(self, model: str = "small"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model)
        device = self.model.model.device
        click.echo(f"[*] Transcription engine: faster-whisper ({device})")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        segments_iter, _info = self.model.transcribe(
            str(audio_path), language=language, word_timestamps=False,
        )
        return [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments_iter]
