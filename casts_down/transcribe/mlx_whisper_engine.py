"""mlx-whisper transcription engine (Apple Silicon Metal)."""
from pathlib import Path
import click
from casts_down.transcribe.engine import Segment, TranscribeEngine

class MLXWhisperEngine(TranscribeEngine):
    def __init__(self, model: str = "small"):
        self.model_name = model
        click.echo("[*] Transcription engine: mlx-whisper (Metal)")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        import mlx_whisper
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{self.model_name}-mlx",
            language=language,
        )
        return [Segment(start=s["start"], end=s["end"], text=s["text"].strip()) for s in result["segments"]]
