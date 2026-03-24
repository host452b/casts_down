"""RSS and Apple Podcasts parsers."""

import re

import aiohttp
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
        异步一次性从 Apple Podcasts 页面提取 RSS URL 和标题
        返回: (rss_url, episode_title)

        性能优化：合并原来的 extract_episode_title() 和 extract_rss_url()，
        避免对同一 URL 发送多次请求
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            async with session.get(apple_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                # 提取标题
                episode_title = None
                title_meta = soup.find('meta', {'property': 'og:title'})
                if title_meta and title_meta.get('content'):
                    episode_title = title_meta['content']
                elif title_tag := soup.find('title'):
                    episode_title = title_tag.text.strip()

                # 提取 RSS URL
                rss_url = None

                # 方式1: 查找 feed URL meta 标签
                feed_meta = soup.find('meta', {'property': 'og:audio'})
                if feed_meta and feed_meta.get('content'):
                    rss_url = feed_meta['content']

                # 方式2: 查找页面中的 RSS 链接
                if not rss_url:
                    rss_link = soup.find('a', href=re.compile(r'https?://.*\.rss'))
                    if rss_link:
                        rss_url = rss_link['href']

                # 方式3: 使用 iTunes API（仅在前两种方式失败时）
                if not rss_url:
                    podcast_id = re.search(r'/id(\d+)', apple_url)
                    if podcast_id:
                        api_url = f"https://itunes.apple.com/lookup?id={podcast_id.group(1)}&entity=podcast"
                        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as api_response:
                            data = await api_response.json()
                            if data.get('resultCount', 0) > 0:
                                rss_url = data['results'][0].get('feedUrl')

                return rss_url, episode_title

        except Exception as e:
            return None, None
