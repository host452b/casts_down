# Transcribe Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add speech-to-text transcription to casts_down with dual-engine support (mlx-whisper Metal + faster-whisper CUDA/CPU), producing SRT + timestamped TXT output.

**Architecture:** Restructure flat modules into a Python package. Add `transcribe/` subpackage with engine ABC, two backends, formatter, and installer. CLI converted to click.group for subcommands. TDD throughout: tests first with mock/dummy engines.

**Tech Stack:** Python 3.10+, click, faster-whisper, mlx-whisper, pytest, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-24-transcribe-feature-design.md`

---

## File Map

### Files to delete (Task 1)

```
setup.py, requirements.txt, ASCII_CHANGELOG.md, XIAOYUZHOU_GUIDE.md,
xiaoyuzhou_technical_report.md, TEST_RESULTS.md, RELEASE_NOTES.md, test_example.sh
```

### Files to create

```
casts_down/                        # Python package
  __init__.py
  cli.py
  downloaders/
    __init__.py
    base.py
    podcast.py
    xiaoyuzhou.py
  transcribe/
    __init__.py
    engine.py
    faster_whisper_engine.py
    mlx_whisper_engine.py
    formatter.py
    installer.py
tests/
  __init__.py
  conftest.py
  test_transcribe_formatter.py
  test_transcribe_engine.py
  test_transcribe_batch.py
  test_transcribe_installer.py
  test_cli.py
  test_downloaders.py
```

### Files to modify

```
pyproject.toml                     # package layout, Python 3.10, optional deps, entry point
```

### Files to delete (old flat modules, after restructure)

```
casts_down.py, podcast_dl.py, xiaoyuzhou_dl.py
```

---

## Task 1: Cleanup — Delete dead files and dead code

**Files:**
- Delete: `setup.py`, `requirements.txt`, `ASCII_CHANGELOG.md`, `XIAOYUZHOU_GUIDE.md`, `xiaoyuzhou_technical_report.md`, `TEST_RESULTS.md`, `RELEASE_NOTES.md`, `test_example.sh`
- Modify: `podcast_dl.py` (remove dead code)
- Modify: `xiaoyuzhou_dl.py` (remove dead code)

- [ ] **Step 1: Delete redundant files**

```bash
cd /Users/joejiang/castdown/casts_down
rm setup.py requirements.txt ASCII_CHANGELOG.md XIAOYUZHOU_GUIDE.md \
   xiaoyuzhou_technical_report.md TEST_RESULTS.md RELEASE_NOTES.md test_example.sh
```

- [ ] **Step 2: Remove dead code from podcast_dl.py**

Remove these sections:
1. `extract_episode_title()` method (lines 183-215) — deprecated, replaced by `extract_metadata_async()`
2. `extract_rss_url()` method (lines 217-256) — deprecated, replaced by `extract_metadata_async()`
3. `print_banner()` function (lines 363-374) — moved to casts_down.py, never called
4. `print_disclaimer()` function (lines 377-397) — moved to casts_down.py, never called
5. Commented-out calls at lines 431-432: `# print_banner()` / `# print_disclaimer()`

- [ ] **Step 3: Remove dead code from xiaoyuzhou_dl.py**

Remove these sections:
1. `print_banner()` function (lines 255-266) — moved to casts_down.py, never called
2. `print_disclaimer()` function (lines 269-289) — moved to casts_down.py, never called
3. Commented-out calls at lines 329-331: `# print_banner()` / `# print_disclaimer()`

- [ ] **Step 4: Verify the tool still works after cleanup**

```bash
python casts_down.py --help
```

Expected: Help text displays correctly, no import errors.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove dead code and redundant files

Delete: setup.py, requirements.txt, ASCII_CHANGELOG.md, XIAOYUZHOU_GUIDE.md,
xiaoyuzhou_technical_report.md, TEST_RESULTS.md, RELEASE_NOTES.md, test_example.sh

Remove deprecated methods: extract_episode_title(), extract_rss_url()
Remove unused print_banner()/print_disclaimer() from podcast_dl.py and xiaoyuzhou_dl.py"
```

---

## Task 2: Restructure — Flat modules to package layout

**Files:**
- Create: `casts_down/__init__.py`, `casts_down/cli.py`, `casts_down/downloaders/__init__.py`, `casts_down/downloaders/base.py`, `casts_down/downloaders/podcast.py`, `casts_down/downloaders/xiaoyuzhou.py`
- Modify: `pyproject.toml`
- Delete (after verified): `casts_down.py`, `podcast_dl.py`, `xiaoyuzhou_dl.py`

- [ ] **Step 1: Create package directory structure**

```bash
cd /Users/joejiang/castdown/casts_down
mkdir -p casts_down/downloaders
```

- [ ] **Step 2: Create `casts_down/__init__.py`**

```python
"""Casts Down - Intelligent Podcast Downloader"""

__version__ = "2.0.0"
```

- [ ] **Step 3: Create `casts_down/downloaders/__init__.py`**

```python
"""Podcast downloaders for various platforms."""
```

- [ ] **Step 4: Create `casts_down/downloaders/base.py`**

Extract from `podcast_dl.py`:
- `PodcastEpisode` class (lines 23-43)
- `PodcastDownloader` class (lines 259-361)

Update imports: these are self-contained, just need `asyncio`, `re`, `pathlib`, `aiohttp`, `click`, `tqdm`, `urllib.parse`.

- [ ] **Step 5: Create `casts_down/downloaders/podcast.py`**

Extract from `podcast_dl.py`:
- `RSSParser` class (lines 45-113)
- `ApplePodcastsParser` class (lines 116-182, only `extract_episode_id` + `extract_metadata_async`)

Update imports to use `from casts_down.downloaders.base import PodcastEpisode`.

- [ ] **Step 6: Create `casts_down/downloaders/xiaoyuzhou.py`**

Extract entire `XiaoyuzhouDownloader` class from `xiaoyuzhou_dl.py` (lines 18-252, minus the deleted print functions). Self-contained.

- [ ] **Step 7: Create `casts_down/cli.py`**

Convert to click.group. This replaces `casts_down.py`, `podcast_dl.py:main()`, and `xiaoyuzhou_dl.py:main()`.

```python
#!/usr/bin/env python3
"""Casts Down - CLI entry point"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import click


def detect_downloader(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if 'xiaoyuzhoufm.com' in domain:
        return 'xiaoyuzhou'
    return 'podcast'


def print_banner():
    banner = "\n🎙️  Casts Down - Intelligent Podcast Downloader v2.0\n"
    click.echo(banner)


def print_disclaimer():
    disclaimer = """
⚠️  DISCLAIMER: For educational purposes only. Respect copyrights.
    该项目仅用于学习，请遵守版权法律法规。
"""
    click.echo(disclaimer)


@click.group(invoke_without_command=True)
@click.argument('url', required=False)
@click.option('--all', '-a', 'download_all', is_flag=True, help='下载所有剧集')
@click.option('--latest', '-l', type=int, default=1, help='下载最新 N 集（默认 1）')
@click.option('--output', '-o', type=click.Path(), default='./podcasts', help='输出目录')
@click.option('--concurrent', '-c', type=int, default=3, help='并发下载数（默认 3）')
@click.option('--skip-existing', '-s', is_flag=True, help='跳过已存在的文件')
@click.option('--transcribe', '-t', is_flag=True, help='下载后自动转写')
@click.option('--model', '-m', default='small', help='Whisper 模型名称或路径（默认 small）')
@click.pass_context
def main(ctx, url, download_all, latest, output, concurrent, skip_existing, transcribe, model):
    """
    Casts Down - 智能播客下载工具

    \b
    支持的平台:
    • Apple Podcasts (podcasts.apple.com)
    • 小宇宙 (xiaoyuzhoufm.com)
    • 通用 RSS 源

    \b
    示例:
    casts-down "https://podcasts.apple.com/podcast/id123" --latest 3
    casts-down "URL" --all --transcribe
    casts-down transcribe ./podcasts/
    casts-down setup-transcribe
    """
    if ctx.invoked_subcommand is not None:
        return

    if url is None:
        click.echo(ctx.get_help())
        return

    print_banner()
    print_disclaimer()

    downloader_type = detect_downloader(url)
    downloaded_files = []

    if downloader_type == 'xiaoyuzhou':
        click.echo("[*] Detected: Xiaoyuzhou Podcast\n")
        _download_xiaoyuzhou(url, output, concurrent, skip_existing, latest, downloaded_files)
    else:
        click.echo(f"[*] Detected: Podcast RSS Feed\n")
        _download_podcast(url, download_all, latest, output, concurrent, skip_existing, downloaded_files)

    if transcribe and downloaded_files:
        try:
            _run_transcription(downloaded_files, model)
        except KeyboardInterrupt:
            click.echo("\n[!] Transcription interrupted by user")
            sys.exit(130)
    elif transcribe:
        click.echo("[!] No files to transcribe (all downloads failed)")


def _download_podcast(url, download_all, latest, output, concurrent, skip_existing, downloaded_files):
    """Run podcast download, append successful file paths to downloaded_files."""
    import asyncio
    import aiohttp
    from casts_down.downloaders.podcast import RSSParser, ApplePodcastsParser
    from casts_down.downloaders.base import PodcastDownloader

    # ... (existing podcast_dl.py main() logic, adapted to collect downloaded_files)
    pass  # Placeholder — full logic extracted from podcast_dl.py:main()


def _download_xiaoyuzhou(url, output, concurrent, skip_existing, latest, downloaded_files):
    """Run xiaoyuzhou download, append successful file paths to downloaded_files."""
    import asyncio
    from casts_down.downloaders.xiaoyuzhou import XiaoyuzhouDownloader

    # ... (existing xiaoyuzhou_dl.py main() logic, adapted to collect downloaded_files)
    pass  # Placeholder — full logic extracted from xiaoyuzhou_dl.py:main()


def _run_transcription(files: list, model: str):
    """Run transcription on list of downloaded files."""
    from casts_down.transcribe import transcribe_batch, print_report
    results = transcribe_batch(files, model=model)
    print_report(results)


@main.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--model', '-m', default='small', help='Whisper 模型名称或路径')
@click.option('--language', default=None, help='语言代码 (zh, en, etc.)')
@click.option('--skip-transcribed', is_flag=True, help='跳过已转写的文件')
@click.option('--overwrite', is_flag=True, help='覆盖已有的转写文件')
def transcribe(path, model, language, skip_transcribed, overwrite):
    """转写音频文件或目录中的所有音频文件"""
    from casts_down.transcribe import transcribe_batch, print_report, collect_audio_files

    target = Path(path)
    if target.is_file():
        files = [target]
    else:
        files = collect_audio_files(target)

    if not files:
        click.echo("[!] No audio files found")
        return

    click.echo(f"[*] Found {len(files)} audio file(s)\n")
    try:
        results = transcribe_batch(
            files, model=model, language=language,
            skip_transcribed=not overwrite and (skip_transcribed or True),
            overwrite=overwrite,
        )
        print_report(results)
    except KeyboardInterrupt:
        click.echo("\n[!] Transcription interrupted by user")
        sys.exit(130)


@main.command('setup-transcribe')
def setup_transcribe():
    """检测环境并安装转写依赖"""
    from casts_down.transcribe.installer import run_setup
    run_setup()
```

Note: `_download_podcast` and `_download_xiaoyuzhou` are placeholders in this plan step. The implementer MUST:
1. Extract the full download logic from `podcast_dl.py:main()` (lines 429-513) into `_download_podcast()`, adapting it to append successfully downloaded `Path` objects to the `downloaded_files` list.
2. Extract the full download logic from `xiaoyuzhou_dl.py:main()` (lines 298-357) into `_download_xiaoyuzhou()`, same adaptation.
3. Preserve the URL-type detection messages ("Apple Podcasts" vs "RSS Feed" vs "Podcast RSS Feed") from the original `casts_down.py` detect_downloader logic.
4. The download functions should import from `casts_down.downloaders.podcast` and `casts_down.downloaders.xiaoyuzhou` respectively.

- [ ] **Step 8: Update `pyproject.toml`**

```toml
[project]
name = "casts_down"
version = "2.0.0"
requires-python = ">=3.10"

[project.scripts]
casts-down = "casts_down.cli:main"

[project.optional-dependencies]
transcribe = ["faster-whisper>=1.0.0,<2.0.0"]
transcribe-metal = [
    "mlx-whisper>=0.4.0,<1.0.0",
    "faster-whisper>=1.0.0,<2.0.0",
]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]

[tool.setuptools.packages.find]
include = ["casts_down*"]
```

Remove the old `[tool.setuptools] py-modules` line. Remove Python 3.8/3.9 classifiers.

- [ ] **Step 9: Delete old flat modules**

```bash
rm casts_down.py podcast_dl.py xiaoyuzhou_dl.py
```

- [ ] **Step 10: Verify the restructured tool works**

```bash
pip install -e .
casts-down --help
casts-down transcribe --help
casts-down setup-transcribe --help
```

Expected: All three help texts display correctly.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "refactor: restructure flat modules into Python package

Convert casts_down.py, podcast_dl.py, xiaoyuzhou_dl.py into:
- casts_down/__init__.py
- casts_down/cli.py (click.group with subcommands)
- casts_down/downloaders/base.py (PodcastEpisode, AsyncDownloader)
- casts_down/downloaders/podcast.py (RSSParser, ApplePodcastsParser)
- casts_down/downloaders/xiaoyuzhou.py (XiaoyuzhouDownloader)

Update pyproject.toml: Python 3.10+, package layout, new entry point.
Bump version to 2.0.0."
```

---

## Task 3: TDD — Transcribe Formatter (pure logic, no mocks)

**Files:**
- Create: `tests/__init__.py`, `tests/conftest.py`, `tests/test_transcribe_formatter.py`
- Create: `casts_down/transcribe/__init__.py`, `casts_down/transcribe/engine.py`, `casts_down/transcribe/formatter.py`

This is the innermost layer — pure data transformation, no I/O, no mocks.

- [ ] **Step 1: Create test infrastructure**

```bash
mkdir -p tests
mkdir -p casts_down/transcribe
```

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
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
```

- [ ] **Step 2: Write failing tests for Segment dataclass and formatter**

`tests/test_transcribe_formatter.py`:
```python
"""Tests for transcription output formatting."""

from pathlib import Path

from casts_down.transcribe.engine import Segment
from casts_down.transcribe.formatter import format_srt, format_txt, write_outputs


class TestSegmentDataclass:
    def test_segment_fields(self):
        s = Segment(start=1.5, end=3.0, text="hello")
        assert s.start == 1.5
        assert s.end == 3.0
        assert s.text == "hello"


class TestFormatSrt:
    def test_basic_srt(self, sample_segments):
        result = format_srt(sample_segments)
        lines = result.strip().split("\n")
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:03,500"
        assert lines[2] == "Hello and welcome to the show."
        assert lines[4] == "2"

    def test_srt_millisecond_precision(self):
        segments = [Segment(start=61.123, end=125.456, text="test")]
        result = format_srt(segments)
        assert "00:01:01,123 --> 00:02:05,456" in result

    def test_srt_hour_overflow(self):
        segments = [Segment(start=3661.0, end=3662.0, text="over an hour")]
        result = format_srt(segments)
        assert "01:01:01,000 --> 01:01:02,000" in result

    def test_empty_segments(self, empty_segments):
        result = format_srt(empty_segments)
        assert result == ""

    def test_chinese_content(self, sample_segments):
        result = format_srt(sample_segments)
        assert "这是一段中文测试内容。" in result


class TestFormatTxt:
    def test_basic_txt(self, sample_segments):
        result = format_txt(sample_segments)
        lines = result.strip().split("\n")
        assert lines[0] == "[00:00:00] Hello and welcome to the show."
        assert lines[1] == "[00:00:03] Today we're going to talk about..."

    def test_txt_second_precision(self):
        segments = [Segment(start=61.9, end=125.0, text="test")]
        result = format_txt(segments)
        assert "[00:01:01]" in result

    def test_empty_segments(self, empty_segments):
        result = format_txt(empty_segments)
        assert result == ""


class TestWriteOutputs:
    def test_writes_srt_and_txt(self, tmp_path, sample_segments):
        audio_path = tmp_path / "episode.mp3"
        audio_path.touch()

        write_outputs(audio_path, sample_segments)

        srt_path = tmp_path / "episode.srt"
        txt_path = tmp_path / "episode.txt"
        assert srt_path.exists()
        assert txt_path.exists()

    def test_utf8_encoding(self, tmp_path, sample_segments):
        audio_path = tmp_path / "episode.mp3"
        audio_path.touch()

        write_outputs(audio_path, sample_segments)

        srt_path = tmp_path / "episode.srt"
        content = srt_path.read_text(encoding="utf-8")
        assert "这是一段中文测试内容。" in content

    def test_no_bom(self, tmp_path, single_segment):
        audio_path = tmp_path / "episode.mp3"
        audio_path.touch()

        write_outputs(audio_path, single_segment)

        raw = (tmp_path / "episode.srt").read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")

    def test_writes_to_temp_then_renames(self, tmp_path, sample_segments):
        """Verify no .tmp files remain after successful write."""
        audio_path = tmp_path / "episode.mp3"
        audio_path.touch()

        write_outputs(audio_path, sample_segments)

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/joejiang/castdown/casts_down
pytest tests/test_transcribe_formatter.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'casts_down.transcribe'`

- [ ] **Step 4: Implement Segment dataclass in `engine.py`**

`casts_down/transcribe/__init__.py`:
```python
"""Transcription support for casts_down."""
```

`casts_down/transcribe/engine.py`:
```python
"""Transcription engine abstract base class and data model."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Segment:
    """A timed text segment from transcription."""
    start: float  # seconds
    end: float    # seconds
    text: str


class TranscribeEngine(ABC):
    """Abstract base class for transcription engines."""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        """
        Transcribe audio file to list of timed segments.

        Args:
            audio_path: Path to audio file.
            language: ISO 639-1 code (e.g. "zh", "en").
                      None = Whisper auto-detect.
        """
        ...
```

- [ ] **Step 5: Implement formatter**

`casts_down/transcribe/formatter.py`:
```python
"""Output formatters for transcription segments."""

from pathlib import Path

from casts_down.transcribe.engine import Segment


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_txt_time(seconds: float) -> str:
    """Format seconds as TXT timestamp: [HH:MM:SS]"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def format_srt(segments: list[Segment]) -> str:
    """Convert segments to SRT subtitle format."""
    if not segments:
        return ""
    parts = []
    for i, seg in enumerate(segments, 1):
        parts.append(f"{i}")
        parts.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        parts.append(seg.text)
        parts.append("")
    return "\n".join(parts)


def format_txt(segments: list[Segment]) -> str:
    """Convert segments to timestamped plain text format."""
    if not segments:
        return ""
    lines = []
    for seg in segments:
        lines.append(f"{_format_txt_time(seg.start)} {seg.text}")
    return "\n".join(lines)


def write_outputs(audio_path: Path, segments: list[Segment]) -> tuple[Path, Path]:
    """
    Write .srt and .txt files next to the audio file.
    Uses temp files for atomic writes.
    Returns (srt_path, txt_path).
    """
    srt_path = audio_path.with_suffix(".srt")
    txt_path = audio_path.with_suffix(".txt")

    srt_tmp = srt_path.with_suffix(".srt.tmp")
    txt_tmp = txt_path.with_suffix(".txt.tmp")

    try:
        srt_tmp.write_text(format_srt(segments), encoding="utf-8")
        txt_tmp.write_text(format_txt(segments), encoding="utf-8")
        srt_tmp.rename(srt_path)
        txt_tmp.rename(txt_path)
    finally:
        for tmp in (srt_tmp, txt_tmp):
            if tmp.exists():
                tmp.unlink()

    return srt_path, txt_path
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_transcribe_formatter.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/test_transcribe_formatter.py tests/__init__.py tests/conftest.py \
       casts_down/transcribe/__init__.py casts_down/transcribe/engine.py \
       casts_down/transcribe/formatter.py
git commit -m "feat: add Segment dataclass and SRT/TXT formatter with tests

TDD: tests written first, pure logic, no external dependencies.
Supports millisecond SRT, second-precision TXT, UTF-8 without BOM,
atomic writes via temp files."
```

---

## Task 4: TDD — Engine detection and fallback logic

**Files:**
- Create: `tests/test_transcribe_engine.py`
- Modify: `casts_down/transcribe/__init__.py` (add `detect_engine()`)
- Create: `casts_down/transcribe/faster_whisper_engine.py`
- Create: `casts_down/transcribe/mlx_whisper_engine.py`

- [ ] **Step 1: Write failing tests for engine detection**

`tests/test_transcribe_engine.py`:
```python
"""Tests for engine detection and fallback logic."""

from unittest.mock import patch, MagicMock
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
    @patch("casts_down.transcribe.platform")
    def test_mac_arm64_prefers_mlx(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"

        with patch.dict("sys.modules", {"mlx_whisper": MagicMock()}):
            from casts_down.transcribe import detect_engine
            # Re-import to pick up patched modules
            import importlib
            import casts_down.transcribe
            importlib.reload(casts_down.transcribe)
            engine = casts_down.transcribe.detect_engine(model="small")
            assert type(engine).__name__ == "MLXWhisperEngine"

    @patch("casts_down.transcribe.platform")
    def test_mac_arm64_falls_back_to_faster_whisper(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"

        with patch.dict("sys.modules", {"mlx_whisper": None}):
            with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
                import importlib
                import casts_down.transcribe
                importlib.reload(casts_down.transcribe)
                engine = casts_down.transcribe.detect_engine(model="small")
                assert type(engine).__name__ == "FasterWhisperEngine"

    @patch("casts_down.transcribe.platform")
    def test_linux_uses_faster_whisper(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"

        with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
            import importlib
            import casts_down.transcribe
            importlib.reload(casts_down.transcribe)
            engine = casts_down.transcribe.detect_engine(model="small")
            assert type(engine).__name__ == "FasterWhisperEngine"

    @patch("casts_down.transcribe.platform")
    def test_no_engine_raises_error(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"

        with patch.dict("sys.modules", {"faster_whisper": None, "mlx_whisper": None}):
            import importlib
            import casts_down.transcribe
            importlib.reload(casts_down.transcribe)
            with pytest.raises(RuntimeError, match="setup-transcribe"):
                casts_down.transcribe.detect_engine(model="small")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_transcribe_engine.py -v
```

Expected: FAIL — `detect_engine` not defined.

- [ ] **Step 3: Implement engine backends (thin wrappers)**

`casts_down/transcribe/faster_whisper_engine.py`:
```python
"""faster-whisper transcription engine."""

from pathlib import Path

import click

from casts_down.transcribe.engine import Segment, TranscribeEngine


class FasterWhisperEngine(TranscribeEngine):
    """Transcription engine using faster-whisper (CTranslate2 backend)."""

    def __init__(self, model: str = "small"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model)
        device = self.model.model.device
        click.echo(f"[*] Transcription engine: faster-whisper ({device})")

    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        segments_iter, _info = self.model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=False,
        )
        return [
            Segment(start=s.start, end=s.end, text=s.text.strip())
            for s in segments_iter
        ]
```

`casts_down/transcribe/mlx_whisper_engine.py`:
```python
"""mlx-whisper transcription engine (Apple Silicon Metal)."""

from pathlib import Path

import click

from casts_down.transcribe.engine import Segment, TranscribeEngine


class MLXWhisperEngine(TranscribeEngine):
    """Transcription engine using mlx-whisper (Apple Metal backend)."""

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
        return [
            Segment(start=s["start"], end=s["end"], text=s["text"].strip())
            for s in result["segments"]
        ]
```

- [ ] **Step 4: Implement `detect_engine()` in `transcribe/__init__.py`**

```python
"""Transcription support for casts_down."""

import platform

import click


def detect_engine(model: str = "small"):
    """
    Detect and return the best available transcription engine.

    Priority:
    - Mac ARM64: mlx-whisper (Metal) > faster-whisper (CPU)
    - Linux/Other: faster-whisper (CUDA/CPU)
    """
    # Try mlx-whisper on Apple Silicon
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401
            from casts_down.transcribe.mlx_whisper_engine import MLXWhisperEngine
            return MLXWhisperEngine(model=model)
        except ImportError:
            click.echo("[*] mlx-whisper not available, falling back to faster-whisper")

    # Try faster-whisper (CUDA auto-detected internally)
    try:
        import faster_whisper  # noqa: F401
        from casts_down.transcribe.faster_whisper_engine import FasterWhisperEngine
        return FasterWhisperEngine(model=model)
    except ImportError:
        pass

    raise RuntimeError(
        "No transcription engine found. Run: casts-down setup-transcribe"
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_transcribe_engine.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_transcribe_engine.py \
       casts_down/transcribe/__init__.py \
       casts_down/transcribe/faster_whisper_engine.py \
       casts_down/transcribe/mlx_whisper_engine.py
git commit -m "feat: add engine detection with mlx-whisper/faster-whisper fallback

TDD: engine detection tests with mocked imports.
Mac ARM64 prefers mlx-whisper (Metal), falls back to faster-whisper.
Linux uses faster-whisper (CUDA auto-detected).
Raises RuntimeError if no engine available."
```

---

## Task 5: TDD — Batch transcription + report

**Files:**
- Create: `tests/test_transcribe_batch.py`
- Modify: `casts_down/transcribe/__init__.py` (add `collect_audio_files()`, `transcribe_batch()`, `print_report()`)

- [ ] **Step 1: Write failing tests**

`tests/test_transcribe_batch.py`:
```python
"""Tests for batch transcription and reporting."""

import time
from pathlib import Path

import pytest

from casts_down.transcribe.engine import Segment, TranscribeEngine


class DummyEngine(TranscribeEngine):
    """Returns fixed segments for testing."""
    def transcribe(self, audio_path, language=None):
        return [
            Segment(0.0, 1.0, "Hello"),
            Segment(1.0, 2.0, "World"),
        ]


class FailingEngine(TranscribeEngine):
    """Always raises an error."""
    def transcribe(self, audio_path, language=None):
        raise RuntimeError("Simulated OOM")


class TestCollectAudioFiles:
    def test_finds_mp3_and_m4a(self, tmp_path):
        (tmp_path / "a.mp3").touch()
        (tmp_path / "b.m4a").touch()
        (tmp_path / "c.txt").touch()

        from casts_down.transcribe import collect_audio_files
        files = collect_audio_files(tmp_path)
        names = {f.name for f in files}
        assert names == {"a.mp3", "b.m4a"}

    def test_empty_directory(self, tmp_path):
        from casts_down.transcribe import collect_audio_files
        assert collect_audio_files(tmp_path) == []

    def test_finds_opus(self, tmp_path):
        (tmp_path / "a.opus").touch()
        from casts_down.transcribe import collect_audio_files
        assert len(collect_audio_files(tmp_path)) == 1


class TestTranscribeBatch:
    def test_success(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.touch()

        from casts_down.transcribe import transcribe_batch
        results = transcribe_batch([audio], engine=DummyEngine())
        assert len(results) == 1
        assert results[0]["success"] is True
        assert (tmp_path / "test.srt").exists()
        assert (tmp_path / "test.txt").exists()

    def test_failure_does_not_block(self, tmp_path):
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        a.touch()
        b.touch()

        from casts_down.transcribe import transcribe_batch
        # First file fails, second succeeds
        class MixedEngine(TranscribeEngine):
            def __init__(self):
                self.call_count = 0
            def transcribe(self, audio_path, language=None):
                self.call_count += 1
                if self.call_count == 1:
                    raise RuntimeError("fail first")
                return [Segment(0.0, 1.0, "ok")]

        results = transcribe_batch([a, b], engine=MixedEngine())
        assert len(results) == 2
        assert results[0]["success"] is False
        assert results[1]["success"] is True

    def test_skip_already_transcribed(self, tmp_path):
        audio = tmp_path / "done.mp3"
        audio.touch()
        (tmp_path / "done.srt").write_text("existing", encoding="utf-8")
        (tmp_path / "done.txt").write_text("existing", encoding="utf-8")

        from casts_down.transcribe import transcribe_batch
        results = transcribe_batch([audio], engine=DummyEngine(), skip_transcribed=True)
        assert results[0]["success"] is True
        assert results[0]["skipped"] is True

    def test_re_transcribe_if_only_srt_exists(self, tmp_path):
        audio = tmp_path / "partial.mp3"
        audio.touch()
        (tmp_path / "partial.srt").write_text("old", encoding="utf-8")
        # .txt missing → should re-transcribe

        from casts_down.transcribe import transcribe_batch
        results = transcribe_batch([audio], engine=DummyEngine(), skip_transcribed=True)
        assert results[0]["skipped"] is False
        assert (tmp_path / "partial.txt").exists()

    def test_overwrite_existing(self, tmp_path):
        audio = tmp_path / "redo.mp3"
        audio.touch()
        (tmp_path / "redo.srt").write_text("old", encoding="utf-8")
        (tmp_path / "redo.txt").write_text("old", encoding="utf-8")

        from casts_down.transcribe import transcribe_batch
        results = transcribe_batch([audio], engine=DummyEngine(), overwrite=True)
        assert results[0]["skipped"] is False
        content = (tmp_path / "redo.srt").read_text(encoding="utf-8")
        assert "Hello" in content

    def test_empty_file_list(self):
        from casts_down.transcribe import transcribe_batch
        results = transcribe_batch([], engine=DummyEngine())
        assert results == []

    def test_keyboard_interrupt_cleans_up(self, tmp_path):
        a = tmp_path / "a.mp3"
        b = tmp_path / "b.mp3"
        a.touch()
        b.touch()

        class InterruptEngine(TranscribeEngine):
            def __init__(self):
                self.call_count = 0
            def transcribe(self, audio_path, language=None):
                self.call_count += 1
                if self.call_count == 2:
                    raise KeyboardInterrupt()
                return [Segment(0.0, 1.0, "ok")]

        from casts_down.transcribe import transcribe_batch
        results = transcribe_batch([a, b], engine=InterruptEngine())
        # Only first file should have results
        assert len(results) == 1
        assert results[0]["success"] is True
        # No .tmp files should remain
        assert list(tmp_path.glob("*.tmp")) == []


class TestPrintReport:
    def test_report_format(self, capsys):
        from casts_down.transcribe import print_report
        results = [
            {"file": Path("a.mp3"), "success": True, "skipped": False, "duration": 3.5, "error": None},
            {"file": Path("b.mp3"), "success": False, "skipped": False, "duration": 0, "error": "OOM"},
        ]
        print_report(results)
        out = capsys.readouterr().out
        assert "1/2 succeeded" in out
        assert "FAILED" in out

    def test_empty_report(self, capsys):
        from casts_down.transcribe import print_report
        print_report([])
        out = capsys.readouterr().out
        assert "No files" in out or out == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_transcribe_batch.py -v
```

Expected: FAIL — `collect_audio_files`, `transcribe_batch`, `print_report` not defined.

- [ ] **Step 3: Implement batch logic in `transcribe/__init__.py`**

Add to existing `casts_down/transcribe/__init__.py`:

```python
import time
from pathlib import Path

import click

from casts_down.transcribe.engine import Segment, TranscribeEngine
from casts_down.transcribe.formatter import write_outputs


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".wma", ".aac", ".opus"}


def collect_audio_files(directory: Path) -> list[Path]:
    """Collect audio files from a directory, sorted by name."""
    return sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )


def _is_transcribed(audio_path: Path) -> bool:
    """Check if both .srt and .txt outputs exist."""
    return audio_path.with_suffix(".srt").exists() and audio_path.with_suffix(".txt").exists()


def transcribe_batch(
    files: list[Path],
    engine: TranscribeEngine | None = None,
    model: str = "small",
    language: str | None = None,
    skip_transcribed: bool = True,
    overwrite: bool = False,
) -> list[dict]:
    """
    Transcribe a list of audio files. Returns list of result dicts.
    Failures do not block subsequent files.
    """
    if engine is None:
        engine = detect_engine(model=model)

    results = []
    for audio_path in files:
        # Skip check
        if not overwrite and skip_transcribed and _is_transcribed(audio_path):
            results.append({
                "file": audio_path,
                "success": True,
                "skipped": True,
                "duration": 0,
                "error": None,
            })
            click.echo(f"[~] Skipped (already transcribed): {audio_path.name}")
            continue

        start_time = time.monotonic()
        try:
            segments = engine.transcribe(audio_path, language=language)
            write_outputs(audio_path, segments)
            elapsed = time.monotonic() - start_time
            results.append({
                "file": audio_path,
                "success": True,
                "skipped": False,
                "duration": elapsed,
                "error": None,
            })
            click.echo(f"[+] {audio_path.name} → .srt + .txt ({elapsed:.0f}s)")
        except KeyboardInterrupt:
            # Clean up partial files
            for suffix in (".srt.tmp", ".txt.tmp"):
                tmp = audio_path.with_suffix(suffix)
                if tmp.exists():
                    tmp.unlink()
            click.echo(f"\n[!] Interrupted during: {audio_path.name}")
            break
        except Exception as e:
            elapsed = time.monotonic() - start_time
            results.append({
                "file": audio_path,
                "success": False,
                "skipped": False,
                "duration": elapsed,
                "error": f"{type(e).__name__}: {e}",
            })
            click.echo(f"[-] {audio_path.name} → FAILED: {type(e).__name__}")

    return results


def print_report(results: list[dict]) -> None:
    """Print a summary report of transcription results."""
    if not results:
        click.echo("[*] No files to report.")
        return

    click.echo("\n=== Transcription Report ===")
    for r in results:
        name = r["file"].name
        if r["skipped"]:
            click.echo(f"[~] {name} → skipped")
        elif r["success"]:
            mins = int(r["duration"] // 60)
            secs = int(r["duration"] % 60)
            click.echo(f"[+] {name} → .srt + .txt ({mins}m{secs:02d}s)")
        else:
            click.echo(f"[-] {name} → FAILED: {r['error']}")

    succeeded = sum(1 for r in results if r["success"])
    click.echo(f"Summary: {succeeded}/{len(results)} succeeded")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_transcribe_batch.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_transcribe_batch.py casts_down/transcribe/__init__.py
git commit -m "feat: add batch transcription with error isolation and reporting

TDD: tests with DummyEngine, no real Whisper dependencies.
Features: collect_audio_files(), transcribe_batch() with skip/overwrite,
print_report() summary, KeyboardInterrupt cleanup."
```

---

## Task 6: TDD — Installer (setup-transcribe)

**Files:**
- Create: `tests/test_transcribe_installer.py`
- Create: `casts_down/transcribe/installer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_transcribe_installer.py`:
```python
"""Tests for setup-transcribe environment detection and installation."""

from unittest.mock import patch, call
import pytest

from casts_down.transcribe.installer import detect_platform, get_install_packages


class TestDetectPlatform:
    @patch("casts_down.transcribe.installer.platform")
    def test_mac_arm64(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        result = detect_platform()
        assert result == "mac_arm64"

    @patch("casts_down.transcribe.installer.platform")
    def test_mac_intel(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "x86_64"
        result = detect_platform()
        assert result == "mac_intel"

    @patch("casts_down.transcribe.installer.platform")
    def test_linux(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        result = detect_platform()
        assert result == "linux"


class TestGetInstallPackages:
    def test_mac_arm64_packages(self):
        pkgs = get_install_packages("mac_arm64")
        assert "mlx-whisper>=0.4.0,<1.0.0" in pkgs
        assert "faster-whisper>=1.0.0,<2.0.0" in pkgs

    def test_mac_intel_packages(self):
        pkgs = get_install_packages("mac_intel")
        assert "faster-whisper>=1.0.0,<2.0.0" in pkgs
        assert not any("mlx" in p for p in pkgs)

    def test_linux_packages(self):
        pkgs = get_install_packages("linux")
        assert "faster-whisper>=1.0.0,<2.0.0" in pkgs
        assert not any("mlx" in p for p in pkgs)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_transcribe_installer.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement installer**

`casts_down/transcribe/installer.py`:
```python
"""Environment detection and transcription dependency installer."""

import platform
import subprocess
import sys

import click


def detect_platform() -> str:
    """Detect current platform for engine selection."""
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin":
        if machine == "arm64":
            return "mac_arm64"
        return "mac_intel"
    return "linux"


def get_install_packages(plat: str) -> list[str]:
    """Return pip packages to install based on platform."""
    base = ["faster-whisper>=1.0.0,<2.0.0"]

    if plat == "mac_arm64":
        return ["mlx-whisper>=0.4.0,<1.0.0"] + base
    return base


def _pip_install(packages: list[str]) -> bool:
    """Run pip install, return True on success."""
    cmd = [sys.executable, "-m", "pip", "install"] + packages
    click.echo(f"[*] Running: pip install {' '.join(packages)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        click.echo(f"[!] pip install failed:\n{result.stderr}", err=True)
        return False
    return True


def _predownload_model(model: str = "small") -> bool:
    """Pre-download the default whisper model."""
    click.echo(f"[*] Downloading model: {model}...")
    try:
        # Try faster-whisper first (always available after install)
        from faster_whisper import WhisperModel
        WhisperModel(model)
        click.echo(f"[+] Model '{model}' ready")
        return True
    except Exception as e:
        click.echo(f"[!] Model download failed: {e}", err=True)
        return False


def run_setup(model: str = "small") -> None:
    """Full setup flow: detect, install, download model."""
    click.echo("[*] Detecting environment...")
    plat = detect_platform()

    labels = {
        "mac_arm64": "macOS arm64 (Apple Silicon)",
        "mac_intel": "macOS x86_64 (Intel)",
        "linux": "Linux",
    }
    click.echo(f"[*] Platform: {labels.get(plat, plat)}")

    packages = get_install_packages(plat)
    click.echo(f"[*] Installing: {', '.join(packages)}")

    if not _pip_install(packages):
        # On Mac ARM64, if mlx-whisper fails, try just faster-whisper
        if plat == "mac_arm64":
            click.echo("[*] Retrying with faster-whisper only...")
            if not _pip_install(["faster-whisper>=1.0.0,<2.0.0"]):
                click.echo("[!] Setup failed. Check error messages above.", err=True)
                sys.exit(1)
        else:
            click.echo("[!] Setup failed. Check error messages above.", err=True)
            sys.exit(1)

    _predownload_model(model)
    click.echo("[+] Setup complete!")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_transcribe_installer.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_transcribe_installer.py casts_down/transcribe/installer.py
git commit -m "feat: add setup-transcribe with platform detection and auto-install

TDD: platform detection and package selection tested with mocks.
Supports: Mac ARM64 (mlx-whisper + faster-whisper), Mac Intel,
Linux (faster-whisper). Fallback on install failure."
```

---

## Task 7: TDD — CLI integration tests

**Files:**
- Create: `tests/test_cli.py`
- Verify: `casts_down/cli.py` (already created in Task 2)

- [ ] **Step 1: Write failing tests for CLI**

`tests/test_cli.py`:
```python
"""Tests for CLI command routing and arguments."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from casts_down.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Casts Down" in result.output

    def test_no_args_shows_help(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "Casts Down" in result.output


class TestTranscribeFlag:
    @patch("casts_down.cli._run_transcription")
    @patch("casts_down.cli._download_podcast")
    def test_transcribe_flag_triggers_transcription(self, mock_dl, mock_tr, runner):
        """--transcribe on download command should call _run_transcription."""
        # Simulate download producing files
        def fake_download(url, dl_all, latest, output, concurrent, skip, files):
            from pathlib import Path
            files.append(Path("/tmp/fake.mp3"))
        mock_dl.side_effect = fake_download

        result = runner.invoke(main, ["https://example.com/feed.rss", "--transcribe"])
        mock_tr.assert_called_once()

    @patch("casts_down.cli._download_podcast")
    def test_no_transcribe_by_default(self, mock_dl, runner):
        """Without --transcribe, _run_transcription should not be called."""
        mock_dl.return_value = None
        with patch("casts_down.cli._run_transcription") as mock_tr:
            result = runner.invoke(main, ["https://example.com/feed.rss"])
            mock_tr.assert_not_called()


class TestTranscribeSubcommand:
    def test_transcribe_help(self, runner):
        result = runner.invoke(main, ["transcribe", "--help"])
        assert result.exit_code == 0
        assert "--model" in result.output
        assert "--language" in result.output

    def test_transcribe_single_file(self, runner, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.touch()

        with patch("casts_down.transcribe.transcribe_batch") as mock_batch, \
             patch("casts_down.transcribe.print_report"), \
             patch("casts_down.transcribe.collect_audio_files"):
            mock_batch.return_value = [
                {"file": audio, "success": True, "skipped": False, "duration": 1.0, "error": None}
            ]
            result = runner.invoke(main, ["transcribe", str(audio)])
        assert result.exit_code == 0


class TestSetupTranscribe:
    def test_setup_help(self, runner):
        result = runner.invoke(main, ["setup-transcribe", "--help"])
        assert result.exit_code == 0

    @patch("casts_down.transcribe.installer.run_setup")
    def test_setup_invokes_run_setup(self, mock_setup, runner):
        result = runner.invoke(main, ["setup-transcribe"])
        mock_setup.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: Some failures if CLI not fully wired.

- [ ] **Step 3: Fix any CLI wiring issues**

Ensure `cli.py` imports and routing work correctly with the transcribe module. Fix any import issues discovered by the tests.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add CLI integration tests for group routing and subcommands

Tests: help output, no-args behavior, transcribe subcommand,
setup-transcribe subcommand. Uses Click CliRunner with mocked backends."
```

---

## Task 8: TDD — Downloader tests (verify restructure didn't break logic)

**Files:**
- Create: `tests/test_downloaders.py`

- [ ] **Step 1: Write tests for extracted downloader logic**

`tests/test_downloaders.py`:
```python
"""Tests for downloader modules after restructure."""

import pytest
from unittest.mock import patch, MagicMock
from casts_down.downloaders.base import PodcastEpisode


class TestPodcastEpisode:
    def test_sanitize_filename_mp3(self):
        ep = PodcastEpisode(
            title="Episode: Test/Title?",
            audio_url="https://example.com/audio.mp3",
        )
        result = ep.sanitize_filename("My Podcast")
        assert result == "My Podcast - Episode TestTitle.mp3"
        assert "/" not in result
        assert "?" not in result
        assert ":" not in result

    def test_sanitize_filename_m4a(self):
        ep = PodcastEpisode(
            title="Test Episode",
            audio_url="https://example.com/audio.m4a",
        )
        result = ep.sanitize_filename("Podcast")
        assert result.endswith(".m4a")

    def test_sanitize_filename_no_extension(self):
        ep = PodcastEpisode(
            title="Test",
            audio_url="https://example.com/audio",
        )
        result = ep.sanitize_filename("Podcast")
        assert result.endswith(".mp3")  # default

    def test_title_length_limit(self):
        ep = PodcastEpisode(
            title="A" * 200,
            audio_url="https://example.com/audio.mp3",
        )
        result = ep.sanitize_filename("P")
        assert len(result) < 200


class TestApplePodcastsParser:
    def test_extract_episode_id(self):
        from casts_down.downloaders.podcast import ApplePodcastsParser
        assert ApplePodcastsParser.extract_episode_id(
            "https://podcasts.apple.com/podcast/id123?i=1000747967318"
        ) == "1000747967318"

    def test_extract_episode_id_no_id(self):
        from casts_down.downloaders.podcast import ApplePodcastsParser
        assert ApplePodcastsParser.extract_episode_id(
            "https://podcasts.apple.com/podcast/id123"
        ) is None


class TestRSSParser:
    def test_parse_valid_rss(self):
        """Test RSS parsing with a mock feedparser response."""
        from casts_down.downloaders.podcast import RSSParser

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Test Podcast"

        entry = MagicMock()
        entry.enclosures = [{"type": "audio/mpeg", "href": "https://example.com/ep.mp3"}]
        entry.get.side_effect = lambda k, d="": {"title": "Episode 1", "published": "2024-01-01"}.get(k, d)
        mock_feed.entries = [entry]

        with patch("casts_down.downloaders.podcast.feedparser.parse", return_value=mock_feed):
            name, episodes = RSSParser.parse("https://example.com/feed.rss")
            assert name == "Test Podcast"
            assert len(episodes) == 1
            assert episodes[0].title == "Episode 1"

    def test_parse_empty_feed(self):
        from casts_down.downloaders.podcast import RSSParser

        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.feed.get.return_value = "Empty Podcast"
        mock_feed.entries = []

        with patch("casts_down.downloaders.podcast.feedparser.parse", return_value=mock_feed):
            name, episodes = RSSParser.parse("https://example.com/feed.rss")
            assert episodes == []


class TestImports:
    def test_import_podcast_parser(self):
        from casts_down.downloaders.podcast import RSSParser, ApplePodcastsParser
        assert RSSParser is not None
        assert ApplePodcastsParser is not None

    def test_import_xiaoyuzhou(self):
        from casts_down.downloaders.xiaoyuzhou import XiaoyuzhouDownloader
        assert XiaoyuzhouDownloader is not None
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_downloaders.py -v
```

Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_downloaders.py
git commit -m "test: add downloader tests to verify restructure correctness

Tests: PodcastEpisode filename sanitization, module imports for
podcast parser, Apple parser, and xiaoyuzhou downloader."
```

---

## Task 9: Final verification — Full test suite + pip install

**Files:** None new — verification only.

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/joejiang/castdown/casts_down
pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 2: Verify editable install**

```bash
pip install -e .
```

Expected: Installs without errors.

- [ ] **Step 3: Verify all CLI commands**

```bash
casts-down --help
casts-down transcribe --help
casts-down setup-transcribe --help
```

Expected: All display help correctly.

- [ ] **Step 4: Verify backward compatibility**

```bash
casts-down "https://feeds.npr.org/510318/podcast.xml" --latest 1
```

Expected: Downloads as before (or shows parsing output if network available).

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```

Only if fixes were needed. Skip if all clean.

- [ ] **Step 6: Tag release**

```bash
git tag v2.0.0
```
