from __future__ import annotations

from dataclasses import dataclass


SECTION_MY_WATCH = "My Watch / 我的关注"
SECTION_AI_BIG_TECH = "AI / Big Tech"
SECTION_TECH_STARTUP = "Tech / Startup"
SECTION_MARKET_FINANCE = "Market / Finance"
SECTION_CHINESE_HOT = "Chinese Hot Topics"

DISPLAY_FEED = "feed"
DISPLAY_RANKING = "ranking"


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    section: str
    displayType: str
    homepageUrl: str
    enabled: bool = True
    refreshIntervalMinutes: int = 30


THEME_ORDER = [
    SECTION_MY_WATCH,
    SECTION_AI_BIG_TECH,
    SECTION_TECH_STARTUP,
    SECTION_MARKET_FINANCE,
    SECTION_CHINESE_HOT,
]

SOURCES: list[SourceConfig] = [
    SourceConfig("openai", "OpenAI", SECTION_AI_BIG_TECH, DISPLAY_FEED, "https://openai.com/news/"),
    SourceConfig(
        "anthropic",
        "Anthropic",
        SECTION_AI_BIG_TECH,
        DISPLAY_FEED,
        "https://www.anthropic.com/news",
    ),
    SourceConfig("google", "Google", SECTION_AI_BIG_TECH, DISPLAY_FEED, "https://blog.google/"),
    SourceConfig(
        "microsoft",
        "Microsoft",
        SECTION_AI_BIG_TECH,
        DISPLAY_FEED,
        "https://blogs.microsoft.com/",
    ),
    SourceConfig("nvidia", "NVIDIA", SECTION_AI_BIG_TECH, DISPLAY_FEED, "https://blogs.nvidia.com/"),
    SourceConfig(
        "intel",
        "Intel",
        SECTION_AI_BIG_TECH,
        DISPLAY_FEED,
        "https://www.intel.com/content/www/us/en/newsroom/home.html",
    ),
    SourceConfig(
        "hacker-news",
        "Hacker News",
        SECTION_TECH_STARTUP,
        DISPLAY_RANKING,
        "https://news.ycombinator.com/",
    ),
    SourceConfig(
        "github-trending",
        "GitHub Trending",
        SECTION_TECH_STARTUP,
        DISPLAY_RANKING,
        "https://github.com/trending",
    ),
    SourceConfig(
        "product-hunt",
        "Product Hunt",
        SECTION_TECH_STARTUP,
        DISPLAY_RANKING,
        "https://www.producthunt.com/",
    ),
    SourceConfig(
        "wallstreetcn",
        "华尔街见闻",
        SECTION_MARKET_FINANCE,
        DISPLAY_FEED,
        "https://wallstreetcn.com/",
    ),
    SourceConfig("cls", "财联社", SECTION_MARKET_FINANCE, DISPLAY_FEED, "https://www.cls.cn/"),
    SourceConfig(
        "zhihu-hot",
        "知乎热榜",
        SECTION_CHINESE_HOT,
        DISPLAY_RANKING,
        "https://www.zhihu.com/hot",
    ),
    SourceConfig(
        "bilibili-popular",
        "哔哩哔哩热门",
        SECTION_CHINESE_HOT,
        DISPLAY_RANKING,
        "https://www.bilibili.com/v/popular/all",
    ),
    SourceConfig(
        "weibo-hot",
        "微博热搜",
        SECTION_CHINESE_HOT,
        DISPLAY_RANKING,
        "https://s.weibo.com/top/summary",
    ),
]

SOURCE_BY_ID = {source.id: source for source in SOURCES}


def get_source(source_id: str) -> SourceConfig:
    return SOURCE_BY_ID[source_id]
