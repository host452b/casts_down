"""mlx-whisper transcription engine (Apple Silicon Metal)."""
import time
from pathlib import Path
import click
from casts_down.transcribe.engine import Segment, TranscribeEngine

class MLXWhisperEngine(TranscribeEngine):
    def __init__(self, model: str = "small"):
        self.model_name = model
        click.echo("[*] Transcription engine: mlx-whisper (Metal)")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        import mlx_whisper

        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        click.echo(f"[*] Transcribing: {audio_path.name} ({file_size_mb:.1f} MB)")

        click.echo(f"[*] Loading model '{self.model_name}' ...")
        t0 = time.monotonic()
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{self.model_name}-mlx",
            language=language,
            verbose=False,
        )
        model_and_transcribe_time = time.monotonic() - t0
        click.echo(f"[*] Model loaded + transcription finished ({model_and_transcribe_time:.1f}s)")

        raw_segments = result.get("segments", [])
        audio_language = result.get("language", "unknown")

        # Derive audio duration from last segment or fallback
        audio_duration = raw_segments[-1]["end"] if raw_segments else 0.0
        audio_mins = int(audio_duration // 60)
        audio_secs = int(audio_duration % 60)
        click.echo(f"[*] Audio duration: {audio_mins}m{audio_secs:02d}s, lang={audio_language}")

        segments = [Segment(start=s["start"], end=s["end"], text=s["text"].strip()) for s in raw_segments]

        elapsed = time.monotonic() - t0
        speed_ratio = audio_duration / elapsed if elapsed > 0 else 0
        click.echo(
            f"[+] Transcription complete: {len(segments)} segments, "
            f"{elapsed:.1f}s ({speed_ratio:.1f}x realtime)"
        )
        return segments
