```
   ____          _         ____
  / ___|__ _ ___| |_ ___  |  _ \  _____      ___ __
 | |   / _` / __| __/ __| | | | |/ _ \ \ /\ / / '_ \
 | |__| (_| \__ \ |_\__ \ | |_| | (_) \ V  V /| | | |
  \____\__,_|___/\__|___/ |____/ \___/ \_/\_/ |_| |_|

      Intelligent Podcast Downloader & Transcriber
```

A cross-platform CLI tool for downloading and transcribing podcasts. Supports Apple Podcasts, Xiaoyuzhou, and RSS feeds with optional local speech-to-text powered by Whisper.

---

## Disclaimer

> **This tool is for EDUCATIONAL and PERSONAL USE ONLY.**
>
> By using this software, you agree to: use for personal learning and research only; respect copyright laws and intellectual property; support content creators through official channels; comply with platform terms of service.
>
> **Prohibited:** commercial redistribution, mass downloading for public sharing, bypassing paid subscriptions, any activity that harms content creators or platforms. The developers fully support and uphold the rights of content creators and platforms.

> **本工具仅供学习和个人使用。**
>
> 使用本软件即表示您同意：仅用于个人学习和研究；尊重版权法律和知识产权；通过官方渠道支持内容创作者；遵守平台服务条款。
>
> **禁止：** 商业性再分发、大规模下载用于公开传播、绕过付费订阅服务、任何损害创作者或平台的行为。开发者拥护并尊重内容创作者和平台的所有权利。

---

## Features

- **Smart URL Detection** - Automatically identifies platform from URL, no need to specify downloader
- **Multi-Platform Support**
  - Apple Podcasts (single episodes and podcast pages)
  - Xiaoyuzhou / 小宇宙 (single episodes and podcast feeds)
  - Standard RSS 2.0 feeds
- **Async Concurrent Downloads** - Configurable concurrency for faster batch downloads
- **Speech-to-Text Transcription** - Local transcription via faster-whisper (CUDA/CPU) or mlx-whisper (Metal)
- **Subtitle Output** - Generates SRT (millisecond precision) and timestamped TXT files
- **Progress Display** - Real-time download and transcription progress tracking
- **Episode Selection** - Download all, latest N, or specific episodes from Apple Podcasts links
- **Smart File Management** - Auto-naming, skip existing files, resume-safe temp files

## Installation

### Option 1: Install via pip (Recommended)

```bash
pip install casts_down
```

### Option 2: Install with transcription support

```bash
# Install base + auto-detect and install best transcription engine
pip install casts_down
casts-down setup-transcribe

# Or manually choose:
# Linux (CUDA/CPU)
pip install "casts_down[transcribe]"

# macOS Apple Silicon (Metal acceleration)
pip install "casts_down[transcribe-metal]"
```

### Option 3: Install from source

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

# Download all episodes from RSS
casts-down "https://feeds.example.com/podcast.rss" --all

# Xiaoyuzhou
casts-down "https://www.xiaoyuzhoufm.com/episode/xxx"

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
| `--skip-existing` | `-s` | Skip already downloaded files | off |
| `--transcribe` | `-t` | Transcribe after download | off |
| `--model NAME` | `-m` | Whisper model for transcription | `small` |

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

### Setup Transcription

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

## Platform Support

### Fully Supported

**Apple Podcasts**
- [x] Podcast homepage (download all or latest N episodes)
- [x] Single episode links (smart matching and download)
- [x] Automatic RSS extraction via iTunes API

**Xiaoyuzhou / 小宇宙**
- [x] Single episode links
- [x] Podcast links (first 15 episodes)
- [ ] Full podcast list (requires additional reverse engineering)

**RSS Feeds**
- [x] Standard RSS 2.0 podcast feeds (most reliable method)

### Not Supported

**Pocket Casts** - Client application, does not host audio files. Use the original podcast RSS feed instead.

## Output Example

```
podcasts/
  My Podcast - Episode 1.mp3
  My Podcast - Episode 1.srt     # SRT subtitle (00:01:23,456 --> 00:01:27,890)
  My Podcast - Episode 1.txt     # [00:01:23] Timestamped plain text
```

## Examples

### Download NPR's "Up First" podcast

```bash
casts-down "https://feeds.npr.org/510318/podcast.xml" --latest 3
```

### Download from Apple Podcasts

```bash
casts-down "https://podcasts.apple.com/us/podcast/the-daily/id1200361736" --all
```

### Download and transcribe

```bash
casts-down "https://feeds.example.com/podcast.rss" --latest 5 --transcribe
```

### Batch download with skip existing

```bash
casts-down "https://feeds.example.com/podcast.rss" --all -o ./downloads --skip-existing
```

### Transcribe a directory of audio files

```bash
casts-down transcribe ./podcasts/ --model medium --language zh
```

## Technical Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| CLI Framework | click |
| HTTP Client | aiohttp (async concurrent) |
| RSS Parsing | feedparser |
| HTML Parsing | BeautifulSoup4 |
| Progress Display | tqdm |
| ASR (optional) | faster-whisper / mlx-whisper |

## Notes

> **Important considerations:**
> 1. **RSS Feed Expiration** - Some feeds may require authentication or contain expired URLs
> 2. **Audio URL Validity** - Some audio URLs contain time-limited tokens that may expire
> 3. **Rate Limiting** - Frequent requests may trigger platform restrictions
> 4. **Copyright** - Ensure all downloads are for personal use only

## Troubleshooting

### Cannot extract Apple Podcasts RSS

- Ensure URL format is correct (must contain podcast ID, e.g. `/id1234567`)
- Check network connection
- Try using the RSS feed URL directly if available

### Download timeout

- Reduce concurrency: `--concurrent 1`
- Check network connection and proxy settings
- Some servers may have rate limiting

### Transcription fails

- Run `casts-down setup-transcribe` to ensure engine is installed
- Try a smaller model: `--model base` or `--model tiny`
- Check available disk space (models are 75MB - 3GB)
- For Chinese content, specify language: `--language zh`

### Abnormal file names

- Tool automatically cleans illegal characters from filenames
- If issues persist, please submit an [Issue](https://github.com/clemente0731/casts_down/issues)

## Quick Test

```bash
# Test RSS parsing
casts-down "https://feeds.npr.org/510318/podcast.xml" --latest 1

# Test Apple Podcasts
casts-down "https://podcasts.apple.com/us/podcast/the-daily/id1200361736" --latest 1

# Test transcription (after setup-transcribe)
casts-down transcribe ./podcasts/episode.mp3 --model tiny
```

## License

MIT License. Copyright (c) 2024 Casts Down Contributors.

## Contributing

Contributions are welcome! Please submit [Issues](https://github.com/clemente0731/casts_down/issues) and Pull Requests.

---

```
Made with <3 by open source contributors
```
