"""Transcription engine abstract base class and data model."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Segment:
    start: float
    end: float
    text: str

class TranscribeEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        ...
