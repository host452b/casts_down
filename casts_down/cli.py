"""
Casts Down - Unified podcast download CLI.

Provides a click.group with backward-compatible default invocation
and subcommands for transcription.
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import click

from casts_down import __version__
from casts_down.downloaders.base import PodcastDownloader
from casts_down.downloaders.podcast import ApplePodcastsParser, RSSParser
from casts_down.downloaders.xiaoyuzhou import XiaoyuzhouDownloader


# ---------------------------------------------------------------------------
# URL detection
# ---------------------------------------------------------------------------

def detect_downloader(url: str) -> str:
    """
    Detect which downloader to use based on URL.

    Returns: 'podcast' or 'xiaoyuzhou'
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if 'xiaoyuzhoufm.com' in domain:
        return 'xiaoyuzhou'

    if 'podcasts.apple.com' in domain or url.endswith('.rss') or url.endswith('.xml'):
        return 'podcast'

    # Default to generic podcast downloader (supports RSS)
    return 'podcast'


# ---------------------------------------------------------------------------
# Download helpers (fully functional, adapted from the original CLIs)
# ---------------------------------------------------------------------------

def _download_podcast(
    url: str,
    download_all: bool,
    latest: int,
    output: str,
    concurrent: int,
    skip_existing: bool,
) -> list[Path]:
    """
    Full podcast download logic (RSS / Apple Podcasts).

    Adapted from podcast_dl.py main().
    Returns list of successfully downloaded file paths.
    """
    downloaded_files: list[Path] = []

    click.echo(f"[*] Parsing: {url}\n")

    # Determine URL type and extract episode info
    rss_url = url
    episode_title = None
    is_single_episode = False

    if 'podcasts.apple.com' in url:
        click.echo("[*] Detected Apple Podcasts URL, extracting info...")

        # Check if this is a single-episode link
        episode_id = ApplePodcastsParser.extract_episode_id(url)
        if episode_id:
            is_single_episode = True
            click.echo(f"[*] Detected episode link")

        # Fetch RSS URL and title in one request
        async def fetch_metadata():
            async with aiohttp.ClientSession() as session:
                return await ApplePodcastsParser.extract_metadata_async(session, url)

        rss_url, episode_title = asyncio.run(fetch_metadata())

        if not rss_url:
            click.echo("[!] Failed to extract RSS URL from Apple Podcasts", err=True)
            sys.exit(1)

        if episode_title:
            click.echo(f"[*] Episode title: {episode_title}")

        click.echo(f"[+] RSS URL: {rss_url}\n")

    # Parse RSS
    podcast_name, episodes = RSSParser.parse(rss_url, episode_title=episode_title)

    if not episodes:
        click.echo("[!] No episodes found", err=True)
        sys.exit(1)

    # Single-episode link with a match
    if is_single_episode and len(episodes) == 1:
        click.echo(f"[*] Podcast: {podcast_name}")
        click.echo(f"[+] Found matching episode: {episodes[0].title}\n")
        selected_episodes = episodes
    else:
        # Normal podcast-link logic
        if is_single_episode:
            click.echo(f"[!] Could not match episode ID, will download latest episode\n")

        click.echo(f"[*] Podcast: {podcast_name}")
        click.echo(f"[*] Total episodes: {len(episodes)}\n")

        # Select episodes
        if download_all:
            selected_episodes = episodes
        else:
            selected_episodes = episodes[:latest]

    click.echo(f"[*] Preparing to download {len(selected_episodes)} episode(s)\n")

    # Download
    output_dir = Path(output)
    downloader = PodcastDownloader(concurrent=concurrent)

    downloaded_files = asyncio.run(downloader.download_all(
        selected_episodes,
        podcast_name,
        output_dir,
        skip_existing,
    ))

    return downloaded_files


def _download_xiaoyuzhou(
    url: str,
    output: str,
    concurrent: int,
    skip_existing: bool,
    latest: int | None,
) -> list[Path]:
    """
    Full Xiaoyuzhou download logic.

    Adapted from xiaoyuzhou_dl.py main().
    Returns list of successfully downloaded file paths.
    """
    downloaded_files: list[Path] = []

    downloader = XiaoyuzhouDownloader(concurrent=concurrent)
    output_dir = Path(output)

    # Determine link type
    if '/episode/' in url:
        # Single episode download
        downloaded_files = asyncio.run(
            downloader.download_episode_by_url(url, output_dir, skip_existing)
        )
    elif '/podcast/' in url:
        # Batch podcast download
        downloaded_files = asyncio.run(
            downloader.download_podcast(url, output_dir, skip_existing, latest)
        )
    else:
        click.echo("[!] Unrecognized URL format", err=True)
        click.echo("Supported formats:", err=True)
        click.echo("  - https://www.xiaoyuzhoufm.com/episode/{eid}", err=True)
        click.echo("  - https://www.xiaoyuzhoufm.com/podcast/{pid}", err=True)
        sys.exit(1)

    return downloaded_files


# ---------------------------------------------------------------------------
# Transcription placeholder
# ---------------------------------------------------------------------------

def _run_transcription(files: list[Path], model: str) -> None:
    """Placeholder for transcription (will be implemented in later tasks)."""
    click.echo(f"\n[*] Transcription requested for {len(files)} file(s) with model '{model}'")
    click.echo("[!] Transcription engine not yet installed. Run: casts-down setup-transcribe")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

class _CastsDownGroup(click.Group):
    """Custom group that allows an optional URL argument alongside subcommands.

    Click normally consumes the first positional token as the URL argument,
    even when it matches a subcommand name.  This override peeks at the
    first non-option token and, if it is a registered subcommand, removes
    the URL argument from the params so Click can route to the subcommand.
    """

    def parse_args(self, ctx, args):
        # Check if first arg looks like a subcommand
        if args and args[0] in self.commands:
            # Temporarily remove the 'url' argument so Click routes to subcommand
            saved_params = self.params
            self.params = [p for p in self.params if p.name != 'url']
            try:
                return super().parse_args(ctx, args)
            finally:
                self.params = saved_params
        return super().parse_args(ctx, args)


@click.group(cls=_CastsDownGroup, invoke_without_command=True)
@click.argument('url', required=False, default=None)
@click.option('--all', '-a', 'download_all', is_flag=True, help='Download all episodes')
@click.option('--latest', '-l', type=int, default=1, help='Download latest N episodes (default: 1)')
@click.option('--output', '-o', type=click.Path(), default='./podcasts', help='Output directory')
@click.option('--concurrent', '-c', type=int, default=3, help='Concurrent downloads (default: 3)')
@click.option('--skip-existing', '-s', is_flag=True, help='Skip existing files')
@click.option('--transcribe', '-t', is_flag=True, help='Transcribe after downloading')
@click.option('--model', '-m', type=str, default='base', help='Whisper model for transcription (default: base)')
@click.option('--version', is_flag=True, help='Show version')
@click.pass_context
def main(ctx, url, download_all, latest, output, concurrent, skip_existing, transcribe, model, version):
    """
    Casts Down - Intelligent Podcast Downloader

    Automatically detects the URL type and uses the appropriate downloader.

    \b
    Supported platforms:
      - Apple Podcasts (podcasts.apple.com)
      - Xiaoyuzhou (xiaoyuzhoufm.com)
      - Generic RSS feeds

    \b
    Examples:
      # Download latest episode from Apple Podcasts
      casts-down "https://podcasts.apple.com/podcast/id123?i=456"

    \b
      # Download latest 3 episodes
      casts-down "https://podcasts.apple.com/podcast/id123" --latest 3

    \b
      # Download from Xiaoyuzhou
      casts-down "https://www.xiaoyuzhoufm.com/episode/xxx"

    \b
      # Download and transcribe
      casts-down "https://feeds.example.com/podcast.rss" --transcribe

    \b
    Subcommands:
      transcribe        Transcribe local audio files
      setup-transcribe  Install transcription dependencies
    """
    if version:
        click.echo(f"casts-down {__version__}")
        return

    # If a subcommand was invoked, skip the default download behavior
    if ctx.invoked_subcommand is not None:
        return

    # No URL and no subcommand => show help
    if url is None:
        click.echo(ctx.get_help())
        return

    try:
        banner = f"\nCasts Down - Intelligent Podcast Downloader v{__version__}\n"
        click.echo(banner)

        disclaimer = (
            "DISCLAIMER: For educational purposes only. Respect copyrights.\n"
        )
        click.echo(disclaimer)

        downloader_type = detect_downloader(url)

        click.echo(f"[*] Detected: ", nl=False)

        downloaded_files: list[Path] = []

        if downloader_type == 'xiaoyuzhou':
            click.echo("Xiaoyuzhou Podcast\n")
            downloaded_files = _download_xiaoyuzhou(
                url=url,
                output=output,
                concurrent=concurrent,
                skip_existing=skip_existing,
                latest=latest if not download_all else None,
            )
        else:  # podcast
            if 'podcasts.apple.com' in url:
                click.echo("Apple Podcasts\n")
            elif url.endswith(('.rss', '.xml')):
                click.echo("RSS Feed\n")
            else:
                click.echo("Podcast RSS Feed\n")

            downloaded_files = _download_podcast(
                url=url,
                download_all=download_all,
                latest=latest,
                output=output,
                concurrent=concurrent,
                skip_existing=skip_existing,
            )

        # Post-download transcription
        if transcribe and downloaded_files:
            _run_transcription(downloaded_files, model)

    except ValueError as e:
        click.echo(f"[!] Error: {str(e)}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\n[!] Download interrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"[!] Unexpected error: {str(e)}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

@main.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--model', '-m', type=str, default='base', help='Whisper model (default: base)')
@click.option('--output', '-o', type=click.Path(), default=None, help='Output directory for transcripts')
def transcribe(files, model, output):
    """Transcribe local audio files.

    \b
    Examples:
      casts-down transcribe recording.mp3
      casts-down transcribe *.mp3 --model large-v3
      casts-down transcribe podcast.m4a -o ./transcripts
    """
    if not files:
        click.echo("[!] No files specified. Usage: casts-down transcribe <file> [file ...]", err=True)
        sys.exit(1)

    file_paths = [Path(f) for f in files]
    _run_transcription(file_paths, model)


@main.command('setup-transcribe')
@click.option('--backend', type=click.Choice(['auto', 'faster-whisper', 'mlx-whisper']),
              default='auto', help='Transcription backend (default: auto-detect)')
def setup_transcribe(backend):
    """Install transcription dependencies.

    \b
    Detects your platform and installs the best transcription backend:
      - macOS Apple Silicon: mlx-whisper (Metal GPU acceleration)
      - Other platforms: faster-whisper (CPU/CUDA)

    \b
    Examples:
      casts-down setup-transcribe
      casts-down setup-transcribe --backend faster-whisper
    """
    click.echo("[*] Transcription setup")
    click.echo(f"[*] Backend: {backend}")
    click.echo("[!] Setup not yet implemented. Coming soon.")
