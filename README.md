# Casts Down

A cross-platform CLI tool for downloading and transcribing podcasts. Supports Apple Podcasts, Xiaoyuzhou, and RSS feeds with optional local speech-to-text powered by Whisper.

## Features

- **Smart URL Detection** - Automatically identifies platform from URL
- **Multi-Platform** - Apple Podcasts, Xiaoyuzhou, RSS 2.0 feeds
- **Async Downloads** - Concurrent downloading with configurable parallelism
- **Speech-to-Text** - Local transcription via faster-whisper (CUDA/CPU) or mlx-whisper (Metal)
- **Subtitle Output** - Generates SRT and timestamped TXT files
- **Batch Processing** - Download and transcribe entire podcast feeds
- **Smart File Management** - Auto-naming, skip existing, resume-safe

## Installation

```bash
pip install casts_down
```

### With transcription support

```bash
# Install base + transcription
pip install casts_down
casts-down setup-transcribe    # auto-detects platform, installs best engine
```

Or manually:

```bash
# Linux (CUDA/CPU)
pip install "casts_down[transcribe]"

# macOS Apple Silicon (Metal acceleration)
pip install "casts_down[transcribe-metal]"
```

### From source

```bash
git clone https://github.com/clemente0731/casts_down.git
cd casts_down
pip install -e ".[dev]"
```

## Quick Start

```bash
# Download latest episode from any podcast URL
casts-down "https://podcasts.apple.com/podcast/id123"

# Download + transcribe
casts-down "https://podcasts.apple.com/podcast/id123" --transcribe

# Download all episodes
casts-down "https://feeds.example.com/podcast.rss" --all

# Transcribe existing audio files
casts-down transcribe ./podcasts/episode.mp3
casts-down transcribe ./podcasts/          # entire directory
```

## Usage

### Download

```bash
casts-down <URL> [OPTIONS]
```

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--all` | `-a` | Download all episodes | latest 1 |
| `--latest N` | `-l N` | Download latest N episodes | 1 |
| `--output DIR` | `-o DIR` | Output directory | `./podcasts` |
| `--concurrent N` | `-c N` | Parallel downloads | 3 |
| `--skip-existing` | `-s` | Skip already downloaded | off |
| `--transcribe` | `-t` | Transcribe after download | off |
| `--model NAME` | `-m` | Whisper model size | `small` |

### Transcribe

```bash
casts-down transcribe <FILE>... [OPTIONS]
```

Transcribe audio files or directories. Outputs `.srt` (subtitle) and `.txt` (timestamped text) alongside each audio file.

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--model NAME` | `-m` | Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`) | `small` |
| `--language CODE` | | Language code (`zh`, `en`, etc.) | auto-detect |
| `--skip-transcribed` | | Skip files already transcribed | on |
| `--overwrite` | | Force re-transcribe existing outputs | off |

### Setup

```bash
casts-down setup-transcribe
```

Detects your platform and installs the optimal transcription engine:

| Platform | Engine | Acceleration |
|----------|--------|-------------|
| macOS Apple Silicon | mlx-whisper + faster-whisper | Metal GPU |
| macOS Intel | faster-whisper | CPU |
| Linux + NVIDIA | faster-whisper | CUDA |
| Linux (no GPU) | faster-whisper | CPU |

## Supported Platforms

| Platform | Single Episode | Batch Download | Notes |
|----------|:---:|:---:|-------|
| Apple Podcasts | Y | Y | Auto RSS extraction |
| Xiaoyuzhou | Y | Y | First 15 episodes via web |
| RSS 2.0 Feeds | Y | Y | Most reliable method |

## Output Example

```
podcasts/
  My Podcast - Episode 1.mp3
  My Podcast - Episode 1.srt     # SRT subtitle
  My Podcast - Episode 1.txt     # [00:01:23] Timestamped text
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| CLI | click |
| HTTP | aiohttp (async) |
| RSS | feedparser |
| HTML Parsing | BeautifulSoup4 |
| ASR (optional) | faster-whisper / mlx-whisper |

## Disclaimer

This tool is for **educational and personal use only**. By using it you agree to respect copyright laws, support content creators through official channels, and comply with platform terms of service. Commercial redistribution of downloaded content is prohibited. The developers assume no liability for misuse.

## License

MIT License. Copyright (c) 2024 Casts Down Contributors.

## Contributing

Issues and Pull Requests welcome at [GitHub](https://github.com/clemente0731/casts_down).
