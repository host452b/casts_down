"""Transcription support for casts_down."""
import platform
import click

def detect_engine(model: str = "small"):
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401
            from casts_down.transcribe.mlx_whisper_engine import MLXWhisperEngine
            return MLXWhisperEngine(model=model)
        except ImportError:
            click.echo("[*] mlx-whisper not available, falling back to faster-whisper")
    try:
        import faster_whisper  # noqa: F401
        from casts_down.transcribe.faster_whisper_engine import FasterWhisperEngine
        return FasterWhisperEngine(model=model)
    except ImportError:
        pass
    raise RuntimeError("No transcription engine found. Run: casts-down setup-transcribe")
