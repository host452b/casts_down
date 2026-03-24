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

class TestImports:
    def test_import_podcast_parser(self):
        from casts_down.downloaders.podcast import RSSParser, ApplePodcastsParser
        assert RSSParser is not None
        assert ApplePodcastsParser is not None

    def test_import_xiaoyuzhou(self):
        from casts_down.downloaders.xiaoyuzhou import XiaoyuzhouDownloader
        assert XiaoyuzhouDownloader is not None
