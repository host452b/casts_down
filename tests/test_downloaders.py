"""Tests for downloader modules after restructure."""
import asyncio
import json
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bs4 import BeautifulSoup

from casts_down.downloaders.base import PodcastEpisode
from casts_down.downloaders.podcast import ApplePodcastsParser

class TestPodcastEpisode:
    def test_sanitize_filename_mp3(self):
        ep = PodcastEpisode(
            title="Episode: Test/Title?",
            audio_url="https://example.com/audio.mp3",
        )
        result = ep.sanitize_filename("My Podcast")
        assert "/" not in result
        assert "?" not in result
        assert ":" not in result
        assert result.endswith(".mp3")

    def test_sanitize_filename_m4a(self):
        ep = PodcastEpisode(title="Test Episode", audio_url="https://example.com/audio.m4a")
        result = ep.sanitize_filename("Podcast")
        assert result.endswith(".m4a")

    def test_sanitize_filename_no_extension(self):
        ep = PodcastEpisode(title="Test", audio_url="https://example.com/audio")
        result = ep.sanitize_filename("Podcast")
        assert result.endswith(".mp3")

    def test_title_length_limit(self):
        ep = PodcastEpisode(title="A" * 200, audio_url="https://example.com/audio.mp3")
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

class TestExtractFeedFromJsonLD:
    """Tests for ApplePodcastsParser._extract_feed_from_jsonld."""

    def test_extracts_top_level_feed_url(self):
        html = '<script type="application/ld+json">{"feedUrl": "https://example.com/feed.rss"}</script>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ApplePodcastsParser._extract_feed_from_jsonld(soup) == "https://example.com/feed.rss"

    def test_extracts_nested_feed_url(self):
        data = {"partOfSeries": {"feedUrl": "https://example.com/nested.rss"}}
        html = f'<script type="application/ld+json">{json.dumps(data)}</script>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ApplePodcastsParser._extract_feed_from_jsonld(soup) == "https://example.com/nested.rss"

    def test_returns_none_when_no_jsonld(self):
        soup = BeautifulSoup('<html><body>No JSON-LD</body></html>', 'html.parser')
        assert ApplePodcastsParser._extract_feed_from_jsonld(soup) is None

    def test_returns_none_for_invalid_json(self):
        html = '<script type="application/ld+json">not valid json</script>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ApplePodcastsParser._extract_feed_from_jsonld(soup) is None

    def test_handles_json_array(self):
        data = [{"@type": "Other"}, {"feedUrl": "https://example.com/array.rss"}]
        html = f'<script type="application/ld+json">{json.dumps(data)}</script>'
        soup = BeautifulSoup(html, 'html.parser')
        assert ApplePodcastsParser._extract_feed_from_jsonld(soup) == "https://example.com/array.rss"


class TestExtractMetadataAsync:
    """Tests for ApplePodcastsParser.extract_metadata_async — independent strategy isolation."""

    @staticmethod
    def _mock_session(*, api_json=None, api_exc=None, page_text=None, page_exc=None):
        """Build a mock aiohttp.ClientSession with configurable API / page responses.

        session.get(url) must be a regular function returning an async context manager
        (matching aiohttp's _RequestContextManager pattern).
        """
        session = MagicMock()

        def fake_get(url, **kwargs):
            ctx = AsyncMock()
            if 'itunes.apple.com' in url:
                if api_exc:
                    ctx.__aenter__ = AsyncMock(side_effect=api_exc)
                else:
                    resp = AsyncMock()
                    resp.json = AsyncMock(return_value=api_json or {"resultCount": 0, "results": []})
                    ctx.__aenter__ = AsyncMock(return_value=resp)
            else:
                if page_exc:
                    ctx.__aenter__ = AsyncMock(side_effect=page_exc)
                else:
                    resp = AsyncMock()
                    resp.raise_for_status = MagicMock()
                    resp.text = AsyncMock(return_value=page_text or '<html></html>')
                    ctx.__aenter__ = AsyncMock(return_value=resp)
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        session.get = fake_get
        return session

    @pytest.mark.asyncio
    async def test_itunes_api_success(self):
        """iTunes API returns feedUrl — page scraping is not needed for RSS."""
        session = self._mock_session(
            api_json={"resultCount": 1, "results": [{"feedUrl": "https://example.com/feed.rss"}]},
        )
        rss, title = await ApplePodcastsParser.extract_metadata_async(
            session, "https://podcasts.apple.com/us/podcast/test/id12345"
        )
        assert rss == "https://example.com/feed.rss"

    @pytest.mark.asyncio
    async def test_page_fail_itunes_api_succeeds(self):
        """Key bug scenario: page fetch fails but iTunes API still returns RSS URL."""
        session = self._mock_session(
            api_json={"resultCount": 1, "results": [{"feedUrl": "https://example.com/feed.rss"}]},
            page_exc=Exception("Connection refused"),
        )
        rss, title = await ApplePodcastsParser.extract_metadata_async(
            session, "https://podcasts.apple.com/us/podcast/test/id12345"
        )
        assert rss == "https://example.com/feed.rss"
        assert title is None  # page was unreachable

    @pytest.mark.asyncio
    async def test_both_fail_returns_none(self):
        """Both strategies fail — returns (None, None) with error output."""
        session = self._mock_session(
            api_exc=Exception("API timeout"),
            page_exc=Exception("Page timeout"),
        )
        rss, title = await ApplePodcastsParser.extract_metadata_async(
            session, "https://podcasts.apple.com/us/podcast/test/id12345"
        )
        assert rss is None
        assert title is None

    @pytest.mark.asyncio
    async def test_itunes_api_fails_falls_back_to_jsonld(self):
        """iTunes API fails but page has JSON-LD with feedUrl."""
        ld_json = json.dumps({"feedUrl": "https://example.com/jsonld.rss"})
        page_html = (
            '<html><head><title>My Podcast</title></head>'
            f'<body><script type="application/ld+json">{ld_json}</script></body></html>'
        )
        session = self._mock_session(
            api_exc=Exception("API error"),
            page_text=page_html,
        )
        rss, title = await ApplePodcastsParser.extract_metadata_async(
            session, "https://podcasts.apple.com/us/podcast/test/id12345"
        )
        assert rss == "https://example.com/jsonld.rss"
        assert title == "My Podcast"

    @pytest.mark.asyncio
    async def test_extracts_episode_title_from_og_meta(self):
        """Page og:title meta tag is used for episode title."""
        page_html = '<html><head><meta property="og:title" content="Episode 42"></head></html>'
        session = self._mock_session(
            api_json={"resultCount": 1, "results": [{"feedUrl": "https://example.com/f.rss"}]},
            page_text=page_html,
        )
        rss, title = await ApplePodcastsParser.extract_metadata_async(
            session, "https://podcasts.apple.com/us/podcast/test/id12345"
        )
        assert title == "Episode 42"

    @pytest.mark.asyncio
    async def test_no_podcast_id_in_url_skips_api(self):
        """URL without /idNNN skips iTunes API entirely."""
        session = self._mock_session(page_text='<html><head><title>Page</title></head></html>')
        rss, title = await ApplePodcastsParser.extract_metadata_async(
            session, "https://podcasts.apple.com/us/podcast/test"
        )
        assert rss is None
        assert title == "Page"


class TestDownloadAll:
    """Tests for PodcastDownloader.download_all — as_completed index tracking."""

    @pytest.mark.asyncio
    async def test_single_episode_download(self):
        """download_all returns correct file path for a single episode."""
        from casts_down.downloaders.base import PodcastDownloader, PodcastEpisode
        import tempfile, aiohttp

        episode = PodcastEpisode(title="Test Ep", audio_url="https://example.com/ep.mp3")
        dl = PodcastDownloader(concurrent=1)

        # Mock download_episode to return success without network
        async def fake_download(session, ep, path, skip):
            path.write_bytes(b"fake audio data")
            return True, f"Done: {path.name}"

        dl.download_episode = fake_download

        with tempfile.TemporaryDirectory() as tmpdir:
            async with aiohttp.ClientSession() as session:
                # Patch session into download_all by mocking ClientSession
                with patch("casts_down.downloaders.base.aiohttp.ClientSession") as mock_cs:
                    mock_cs.return_value.__aenter__ = AsyncMock(return_value=session)
                    mock_cs.return_value.__aexit__ = AsyncMock(return_value=False)
                    files = await dl.download_all([episode], "Podcast", Path(tmpdir))

        assert len(files) == 1
        assert "Test Ep" in files[0].name

    @pytest.mark.asyncio
    async def test_multiple_episodes_all_tracked(self):
        """download_all correctly tracks indices for multiple concurrent episodes."""
        from casts_down.downloaders.base import PodcastDownloader, PodcastEpisode
        import tempfile, aiohttp

        episodes = [
            PodcastEpisode(title=f"Ep {i}", audio_url=f"https://example.com/ep{i}.mp3")
            for i in range(5)
        ]
        dl = PodcastDownloader(concurrent=3)

        async def fake_download(session, ep, path, skip):
            path.write_bytes(b"data")
            return True, f"Done: {path.name}"

        dl.download_episode = fake_download

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("casts_down.downloaders.base.aiohttp.ClientSession") as mock_cs:
                mock_cs.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
                mock_cs.return_value.__aexit__ = AsyncMock(return_value=False)
                files = await dl.download_all(episodes, "Podcast", Path(tmpdir))

        assert len(files) == 5
        titles = {f.stem for f in files}
        for i in range(5):
            assert any(f"Ep {i}" in t for t in titles)

    @pytest.mark.asyncio
    async def test_partial_failure_tracked(self):
        """download_all returns only successful files when some downloads fail."""
        from casts_down.downloaders.base import PodcastDownloader, PodcastEpisode
        import tempfile

        episodes = [
            PodcastEpisode(title="Good", audio_url="https://example.com/good.mp3"),
            PodcastEpisode(title="Bad", audio_url="https://example.com/bad.mp3"),
        ]
        dl = PodcastDownloader(concurrent=2)

        async def fake_download(session, ep, path, skip):
            if "Bad" in ep.title:
                return False, f"Failed: {ep.title}"
            path.write_bytes(b"data")
            return True, f"Done: {path.name}"

        dl.download_episode = fake_download

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("casts_down.downloaders.base.aiohttp.ClientSession") as mock_cs:
                mock_cs.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
                mock_cs.return_value.__aexit__ = AsyncMock(return_value=False)
                files = await dl.download_all(episodes, "Podcast", Path(tmpdir))

        assert len(files) == 1
        assert "Good" in files[0].name


class TestImports:
    def test_import_podcast_parser(self):
        from casts_down.downloaders.podcast import RSSParser, ApplePodcastsParser
        assert RSSParser is not None
        assert ApplePodcastsParser is not None

    def test_import_xiaoyuzhou(self):
        from casts_down.downloaders.xiaoyuzhou import XiaoyuzhouDownloader
        assert XiaoyuzhouDownloader is not None
