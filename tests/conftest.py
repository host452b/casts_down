"""Shared test fixtures."""
import pytest
from casts_down.transcribe.engine import Segment

@pytest.fixture
def sample_segments():
    return [
        Segment(start=0.0, end=3.5, text="Hello and welcome to the show."),
        Segment(start=3.5, end=7.2, text="Today we're going to talk about..."),
        Segment(start=7.2, end=12.0, text="这是一段中文测试内容。"),
    ]

@pytest.fixture
def empty_segments():
    return []

@pytest.fixture
def single_segment():
    return [Segment(start=0.0, end=1.0, text="Just one segment.")]
