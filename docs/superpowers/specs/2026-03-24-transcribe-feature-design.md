# Transcribe Feature Design

## Overview

Add speech-to-text transcription to casts_down. After downloading podcast audio, automatically transcribe to timestamped subtitle files (SRT + plain text). Also support standalone transcription of existing audio files.

## Goals

- Zero-compilation installation via pip
- Cross-platform: Mac (Metal preferred, CPU fallback) + Linux (CUDA preferred, CPU fallback)
- Model auto-download on first use (default: whisper-small)
- TDD: tests first, mock/dummy external dependencies

## Non-Goals

- Real-time streaming transcription
- Speaker diarization
- Translation (transcribe only, no language conversion)

---

## Python Version

Minimum Python version bumped to **3.10** (for `str | None` union syntax and modern typing).

```toml
requires-python = ">=3.10"
```

---

## Code Cleanup (Pre-restructure)

Remove dead code and useless files before restructuring:

### Files to delete

| File | Reason |
|------|--------|
| `setup.py` | Redundant — pyproject.toml handles all packaging |
| `requirements.txt` | Redundant — dependencies defined in pyproject.toml |
| `ASCII_CHANGELOG.md` | Not a real changelog, just documents emoji→ASCII formatting change |
| `XIAOYUZHOU_GUIDE.md` | Content duplicated across TEST_RESULTS.md and technical report |
| `xiaoyuzhou_technical_report.md` | Content duplicated; unique bits merged into LIMITATIONS.md |
| `TEST_RESULTS.md` | Duplicated across multiple Xiaoyuzhou docs |
| `RELEASE_NOTES.md` | Use git tags/releases instead |
| `test_example.sh` | Not a real test suite; replaced by pytest tests |

### Dead code to remove

| Location | What | Reason |
|----------|------|--------|
| `podcast_dl.py:184-215` | `extract_episode_title()` | Deprecated, replaced by `extract_metadata_async()`, never called |
| `podcast_dl.py:218-256` | `extract_rss_url()` | Deprecated, replaced by `extract_metadata_async()`, never called |
| `podcast_dl.py:363-397` | `print_banner()`, `print_disclaimer()` | Moved to casts_down.py, never called |
| `podcast_dl.py:431-432` | Commented-out `print_banner()`/`print_disclaimer()` calls | Dead comments |
| `xiaoyuzhou_dl.py:255-289` | `print_banner()`, `print_disclaimer()` | Moved to casts_down.py, never called |
| `xiaoyuzhou_dl.py:330-331` | Commented-out `print_banner()`/`print_disclaimer()` calls | Dead comments |

---

## Code Restructure

### Current (flat modules)

```
casts_down/
  casts_down.py
  podcast_dl.py
  xiaoyuzhou_dl.py
  pyproject.toml
```

### Target (package layout)

```
casts_down/                          # project root
  pyproject.toml
  README.md
  LIMITATIONS.md
  BUILD.md
  Makefile
  build_exe.py
  tests/
    __init__.py
    conftest.py                      # shared fixtures, dummy audio generator
    test_cli.py
    test_downloaders.py
    test_transcribe_engine.py
    test_transcribe_formatter.py
    test_transcribe_installer.py
    test_transcribe_batch.py
  casts_down/                        # Python package
    __init__.py                      # __version__
    cli.py                           # Click group + commands
    downloaders/
      __init__.py
      base.py                        # PodcastEpisode, AsyncDownloader
      podcast.py                     # RSSParser, ApplePodcastsParser
      xiaoyuzhou.py                  # XiaoyuzhouDownloader
    transcribe/
      __init__.py                    # detect_engine(), transcribe_batch()
      engine.py                      # TranscribeEngine ABC + Segment dataclass
      faster_whisper_engine.py       # FasterWhisperEngine
      mlx_whisper_engine.py          # MLXWhisperEngine
      formatter.py                   # SRT + TXT output
      installer.py                   # setup-transcribe env detection + install
```

Note: `transcribe/installer.py` (not `setup.py`) to avoid naming collision with the root-level legacy `setup.py` during migration.

### Responsibility per file (soft LOC targets)

| File | Responsibility | Target LOC |
|------|---------------|------------|
| `cli.py` | Click group + command routing, arg definitions, no business logic | ~150 |
| `downloaders/base.py` | Episode dataclass, async downloader, filename sanitization | ~100 |
| `downloaders/podcast.py` | RSS parsing, Apple Podcasts metadata extraction | ~150 |
| `downloaders/xiaoyuzhou.py` | Xiaoyuzhou page scraping, API interaction | ~150 |
| `transcribe/engine.py` | ABC + Segment dataclass | ~30 |
| `transcribe/faster_whisper_engine.py` | faster-whisper implementation | ~60 |
| `transcribe/mlx_whisper_engine.py` | mlx-whisper implementation | ~60 |
| `transcribe/formatter.py` | Segment list -> .srt / .txt files | ~100 |
| `transcribe/installer.py` | Platform detection, pip install orchestration | ~80 |
| `transcribe/__init__.py` | `detect_engine()`, `transcribe_batch()`, `print_report()` | ~80 |

### pyproject.toml changes

```toml
[project]
requires-python = ">=3.10"

[project.scripts]
casts-down = "casts_down.cli:main"

[tool.setuptools.packages.find]
include = ["casts_down*"]
```

Remove `py-modules` and the old `[tool.setuptools]` section.

---

## CLI Architecture

Converting from `@click.command` to `@click.group` with `invoke_without_command=True` to preserve backward compatibility.

### Command structure

```
casts-down                           # group (default: download mode)
  ├── [default]                      # download (backward-compatible, no subcommand needed)
  ├── transcribe <path>              # standalone transcription
  └── setup-transcribe               # install transcription dependencies
```

### Download mode (default, backward-compatible)

```bash
# These all work exactly as before:
casts-down "URL"
casts-down "URL" --all
casts-down "URL" --latest 3 --output ./podcasts

# New flag added:
casts-down "URL" --all --transcribe
casts-down "URL" --transcribe --model medium
```

Existing flags (`--all`, `--latest`, `--output`, `--concurrent`, `--skip-existing`) remain on the default download command. `--transcribe` and `--model` are added alongside them.

### Standalone transcribe subcommand

```bash
casts-down transcribe ./podcasts/episode.mp3
casts-down transcribe ./podcasts/
casts-down transcribe ./podcasts/ --model medium --language zh
casts-down transcribe ./podcasts/ --skip-transcribed
```

### Setup subcommand

```bash
casts-down setup-transcribe
```

---

## Transcription Engine

### Data Model

```python
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path

@dataclass
class Segment:
    start: float   # seconds
    end: float     # seconds
    text: str

class TranscribeEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language: str | None = None) -> list[Segment]:
        """
        Transcribe audio file to list of timed segments.

        Args:
            audio_path: Path to audio file
            language: ISO 639-1 code (e.g. "zh", "en").
                      None = Whisper auto-detect (works well for single-language audio,
                      may be unreliable for mixed zh/en content).
        """
        ...
```

### Engine Priority

| Platform | Primary | Fallback |
|----------|---------|----------|
| Mac Apple Silicon | mlx-whisper (Metal) | faster-whisper (CPU ARM NEON) |
| Mac Intel | faster-whisper (CPU) | - |
| Linux + NVIDIA GPU | faster-whisper (CUDA) | faster-whisper (CPU) |
| Linux no GPU | faster-whisper (CPU) | - |

Detection logic in `detect_engine()`:

```
1. platform.system() == "Darwin" and platform.machine() == "arm64"
   → try import mlx_whisper → MLXWhisperEngine
   → on ImportError: print fallback message, continue to step 2
2. try import faster_whisper → FasterWhisperEngine
   → auto-detects CUDA availability internally
3. neither available → raise RuntimeError("No transcription engine found. Run: casts-down setup-transcribe")
```

Engine selection always printed:
```
[*] Transcription engine: mlx-whisper (Metal)
```
```
[*] mlx-whisper not available, using faster-whisper (CPU)
```

### Model resolution

The `--model` flag accepts:
1. **Model name** (e.g. `small`, `medium`, `large-v3`) — passed directly to engine, which handles download/cache
2. **Local path** (e.g. `./models/my-whisper`) — detected by checking `Path(value).exists()`
3. **Invalid value** — engine raises error, caught and reported

Default: `small`

---

## Supported Audio Formats

For directory-mode transcription, the following extensions are scanned:

```python
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".wma", ".aac", ".opus"}
```

Files not matching these extensions are silently skipped.

---

## Output Format

For each audio file, generate two sibling files:

```
podcasts/
  episode.mp3
  episode.srt          # SRT subtitle (millisecond precision)
  episode.txt          # Timestamped plain text (second precision, intentional for readability)
```

Output encoding: **UTF-8 without BOM** (standard for SRT and modern text editors; works correctly with CJK content).

### SRT Format (millisecond precision)

```
1
00:00:00,000 --> 00:00:03,500
Hello and welcome to the show.

2
00:00:03,500 --> 00:00:07,200
Today we're going to talk about...
```

### TXT Format (second precision, for readability)

```
[00:00:00] Hello and welcome to the show.
[00:00:03] Today we're going to talk about...
```

### Overwrite behavior

- Default: **skip** files where both `.srt` and `.txt` already exist (safe for re-runs)
- If only one output exists (e.g. `.srt` but no `.txt`), **re-transcribe** to produce both
- `--skip-transcribed` flag: explicit skip (same as default, for clarity in scripts)
- `--overwrite` flag: force re-transcribe and overwrite existing output

---

## Error Handling

### Per-file resilience

- Each transcription wrapped in try/except
- Failure on one file does not block subsequent files
- Failed files recorded with error message and exception type

### Zero successful downloads

If `--transcribe` is used but all downloads failed:
```
[!] No files to transcribe (all downloads failed)
```
Transcription phase skipped entirely.

### Model download failure

- Network timeout or partial download → engine libraries handle retry/cleanup internally
- Corrupt cache → user directed to clear cache and re-run `setup-transcribe`
- Error message: `[!] Model download failed: <details>. Try: casts-down setup-transcribe`

### setup-transcribe pip install failure

- Capture pip stderr, display to user
- If primary engine install fails on Mac, attempt fallback (faster-whisper only)
- Always report final state: what was installed, what failed

### KeyboardInterrupt during transcription

- Catch `KeyboardInterrupt` in the batch loop
- Clean up partial `.srt.tmp` / `.txt.tmp` files (write to temp, rename on completion)
- Print partial report for files completed before interruption
- Exit with code 130 (consistent with download interrupt behavior)

### Summary report (printed after all tasks complete)

```
=== Transcription Report ===
[+] episode1.mp3 → .srt + .txt (3m12s)
[+] episode2.mp3 → .srt + .txt (5m01s)
[-] episode3.mp3 → FAILED: OutOfMemoryError
Summary: 2/3 succeeded
```

---

## Dependencies

### pyproject.toml

```toml
[project.optional-dependencies]
transcribe = ["faster-whisper>=1.0.0,<2.0.0"]
transcribe-metal = [
    "mlx-whisper>=0.4.0,<1.0.0",
    "faster-whisper>=1.0.0,<2.0.0",
]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
```

Version upper bounds added: faster-whisper pinned below 2.0, mlx-whisper pinned below 1.0 (pre-1.0 library with potential breaking changes in minor versions).

### Transitive dependencies (acknowledged)

- `faster-whisper` → `ctranslate2` (has platform-specific wheels; Linux x86_64, macOS x86_64/arm64 covered; exotic architectures may fail)
- `mlx-whisper` → `mlx` (Apple-only; will fail to install on Linux, which is fine since it's only in `transcribe-metal` extra)
- CUDA support: `ctranslate2` wheels auto-detect CUDA toolkit; no additional pip install needed

### Model Management

- Default model: `small` (~466 MB)
- Auto-downloaded to library's default cache dir on first use
- `setup-transcribe` pre-downloads the model so first `--transcribe` run has zero wait
- User override via `--model` flag (model name or local path)

---

## TDD Approach

Tests written before implementation. External dependencies (faster-whisper, mlx-whisper, network) mocked/dummied.

### Test Plan

| Test File | What It Tests | Mock/Dummy |
|-----------|---------------|------------|
| `test_cli.py` | Click group routing, --transcribe flag, transcribe subcommand, backward compat | Click CliRunner, mock transcribe_batch |
| `test_downloaders.py` | RSS parsing, Apple URL extraction, filename sanitization, .m4a handling | feedparser data, HTTP responses |
| `test_transcribe_engine.py` | Engine detection, fallback chain, ABC contract, import error handling | Mock platform, mock imports |
| `test_transcribe_formatter.py` | Segment→SRT, Segment→TXT, UTF-8 encoding, empty segments, edge cases | Pure logic, no mocks |
| `test_transcribe_installer.py` | Platform detection, install command generation, pip failure handling | Mock platform/subprocess |
| `test_transcribe_batch.py` | Batch transcription, error isolation, report generation, skip-transcribed, overwrite, KeyboardInterrupt, zero-file edge case | DummyEngine (returns fixed Segments) |
