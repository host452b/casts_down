"""RSS and Apple Podcasts parsers."""

import json
import re

import aiohttp
import click
import feedparser
from bs4 import BeautifulSoup

from casts_down.downloaders.base import PodcastEpisode


class RSSParser:
    """RSS 解析器"""

    @staticmethod
    def parse(rss_url: str, episode_title: str | None = None) -> tuple[str, list[PodcastEpisode]]:
        """
        解析 RSS 源
        返回: (播客名称, 剧集列表)

        参数:
            rss_url: RSS 源地址
            episode_title: 可选的单集标题，如果提供则只返回匹配的剧集
        """
        try:
            feed = feedparser.parse(rss_url)

            if feed.bozo and not feed.entries:  # 解析错误且无有效条目
                raise ValueError(f"RSS 解析失败: {feed.bozo_exception}")

            podcast_name = feed.feed.get('title', 'Unknown Podcast')
            episodes = []

            for entry in feed.entries:
                # 查找音频链接
                audio_url = None

                # 方式1: enclosures
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    for enc in entry.enclosures:
                        if 'audio' in enc.get('type', ''):
                            audio_url = enc.get('href')
                            break

                # 方式2: links
                if not audio_url and hasattr(entry, 'links'):
                    for link in entry.links:
                        if link.get('type', '').startswith('audio'):
                            audio_url = link.get('href')
                            break

                if audio_url:
                    episode = PodcastEpisode(
                        title=entry.get('title', 'Untitled'),
                        audio_url=audio_url,
                        published=entry.get('published', '')
                    )

                    # 如果指定了单集标题，检查是否匹配
                    if episode_title:
                        # 清理标题进行模糊匹配
                        rss_title = episode.title.strip().lower()
                        target_title = episode_title.strip().lower()

                        # 移除播客名称（可能在 Apple Podcasts 标题中）
                        podcast_name_lower = podcast_name.lower()
                        target_title = target_title.replace(podcast_name_lower, '').strip()
                        target_title = target_title.lstrip(':：- ')

                        # 检查标题是否匹配（包含或被包含）
                        if target_title in rss_title or rss_title in target_title:
                            episodes = [episode]  # 只保留匹配的剧集
                            break
                    else:
                        episodes.append(episode)

            return podcast_name, episodes

        except Exception as e:
            raise ValueError(f"RSS 解析错误: {str(e)}")


class ApplePodcastsParser:
    """Apple Podcasts URL 处理器"""

    @staticmethod
    def extract_episode_id(apple_url: str) -> str | None:
        """
        从 Apple Podcasts URL 提取单集 ID
        例如: ?i=1000747967318 -> 1000747967318
        """
        match = re.search(r'[?&]i=(\d+)', apple_url)
        return match.group(1) if match else None

    @staticmethod
    async def extract_metadata_async(session: aiohttp.ClientSession, apple_url: str) -> tuple[str | None, str | None]:
        """
        从 Apple Podcasts URL 提取 RSS URL 和单集标题。
        返回: (rss_url, episode_title)

        按可靠性顺序尝试多种策略：
        1. iTunes Lookup API（最可靠，结构化数据）
        2. 页面 JSON-LD 结构化数据
        3. 页面 meta 标签 / RSS 链接（兼容旧版）

        每种策略使用独立的 try 块，避免单点失败导致全部跳过。
        """
        rss_url = None
        episode_title = None

        # ── 策略1: iTunes Lookup API（最可靠） ──────────────────────
        podcast_id_match = re.search(r'/id(\d+)', apple_url)
        if podcast_id_match:
            try:
                api_url = (
                    f"https://itunes.apple.com/lookup"
                    f"?id={podcast_id_match.group(1)}&entity=podcast"
                )
                async with session.get(
                    api_url, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    data = await resp.json(content_type=None)
                    if data.get('resultCount', 0) > 0:
                        rss_url = data['results'][0].get('feedUrl')
            except Exception as e:
                click.echo(f"[!] iTunes API lookup failed: {e}", err=True)

        # ── 策略2: 页面抓取（获取单集标题，RSS URL 作为备选） ────────
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36'
                )
            }
            async with session.get(
                apple_url, headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                response.raise_for_status()
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                # 提取标题
                title_meta = soup.find('meta', {'property': 'og:title'})
                if title_meta and title_meta.get('content'):
                    episode_title = title_meta['content']
                elif title_tag := soup.find('title'):
                    episode_title = title_tag.text.strip()

                # 仅在 iTunes API 未成功时，从页面提取 RSS URL
                if not rss_url:
                    # 方式A: JSON-LD 结构化数据（Apple 当前使用的格式）
                    rss_url = ApplePodcastsParser._extract_feed_from_jsonld(soup)

                if not rss_url:
                    # 方式B: og:audio meta 标签（兼容旧版）
                    feed_meta = soup.find('meta', {'property': 'og:audio'})
                    if feed_meta and feed_meta.get('content'):
                        rss_url = feed_meta['content']

                if not rss_url:
                    # 方式C: 页面中的 RSS/XML 链接（兼容旧版）
                    rss_link = soup.find(
                        'a', href=re.compile(r'https?://.*\.(rss|xml)')
                    )
                    if rss_link:
                        rss_url = rss_link['href']
        except Exception as e:
            click.echo(f"[!] Apple Podcasts page fetch failed: {e}", err=True)

        return rss_url, episode_title

    @staticmethod
    def _extract_feed_from_jsonld(soup: BeautifulSoup) -> str | None:
        """从页面 JSON-LD 结构化数据中提取 feedUrl。"""
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    feed = item.get('feedUrl')
                    if feed:
                        return feed
                    # 检查嵌套对象（partOfSeries 等）
                    for key in ('partOfSeries', 'mainEntity'):
                        nested = item.get(key)
                        if isinstance(nested, dict):
                            feed = nested.get('feedUrl')
                            if feed:
                                return feed
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
        return None
