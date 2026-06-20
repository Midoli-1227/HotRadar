from __future__ import annotations

import os

from ..sources import SOURCE_BY_ID, SOURCES, SourceConfig
from .base import Collector
from .fixtures import FixtureCollector
from .http import (
    AnthropicNewsCollector,
    BaiduHotCollector,
    BilibiliPopularCollector,
    ClsHomeCollector,
    GitHubTrendingCollector,
    HackerNewsCollector,
    ProductHuntFeedCollector,
    RSSCollector,
    UnsupportedCollector,
    WallstreetcnLiveCollector,
    WeiboHotCollector,
    ZhihuHotCollector,
)


RSS_FEEDS = {
    "openai": "https://openai.com/news/rss.xml",
    "google": "https://blog.google/technology/ai/rss/",
    "microsoft": "https://blogs.microsoft.com/feed/",
    "nvidia": "https://blogs.nvidia.com/feed/",
    "intel": "https://www.intc.com/news-events/press-releases/rss",
}

UNSUPPORTED_REASONS: dict[str, str] = {}


def collector_for_source(source: SourceConfig) -> Collector:
    mode = os.getenv("HOTRADAR_COLLECTOR_MODE", "hybrid")
    if mode == "fixture":
        return FixtureCollector(source)

    if source.id in RSS_FEEDS:
        return RSSCollector(source, RSS_FEEDS[source.id])
    if source.id == "anthropic":
        return AnthropicNewsCollector(source)
    if source.id == "hacker-news":
        return HackerNewsCollector(source)
    if source.id == "github-trending":
        return GitHubTrendingCollector(source)
    if source.id == "product-hunt":
        return ProductHuntFeedCollector(source)
    if source.id == "wallstreetcn":
        return WallstreetcnLiveCollector(source)
    if source.id == "cls":
        return ClsHomeCollector(source)
    if source.id == "zhihu-hot":
        return ZhihuHotCollector(source)
    if source.id == "bilibili-popular":
        return BilibiliPopularCollector(source)
    if source.id == "weibo-hot":
        return WeiboHotCollector(source)
    if source.id == "baidu-hot":
        return BaiduHotCollector(source)

    return UnsupportedCollector(
        source,
        UNSUPPORTED_REASONS.get(
            source.id,
            f"No stable collector implemented for {source.name}; source position is retained.",
        ),
    )


def build_collectors() -> dict[str, Collector]:
    return {source.id: collector_for_source(source) for source in SOURCES if source.enabled}

def get_fixture_collector(source_id: str) -> FixtureCollector:
    return FixtureCollector(SOURCE_BY_ID[source_id])
