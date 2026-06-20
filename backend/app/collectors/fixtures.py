from __future__ import annotations

from ..schemas import HotItem, utc_now
from ..sources import SourceConfig


class FixtureCollector:
    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        now = utc_now()
        keywords = [
            "AI",
            "OpenAI",
            "NVIDIA",
            "芯片",
            "美股",
            "Google",
            "ChatGPT",
            "半导体",
        ]
        items = []
        for index in range(1, 9):
            keyword = keywords[(index - 1) % len(keywords)]
            title = f"{self.source.name} demo radar item {index}: {keyword} update"
            if self.source.section == "Chinese Hot Topics":
                title = f"{self.source.name} 示例热点 {index}: {keyword} 讨论升温"
            elif self.source.section == "Market / Finance":
                title = f"{self.source.name} market watch {index}: {keyword} signal"
            items.append(
                HotItem(
                    source=self.source.id,
                    section=self.source.section,
                    rank=index,
                    title=title,
                    url=f"{self.source.homepageUrl.rstrip('/')}/?hotradar_demo={index}",
                    heat=f"{1000 - index * 37}",
                    summary=f"Offline fixture for {self.source.name}; useful when a live source is unavailable.",
                    fetchedAt=now,
                    extra={"mode": "fixture", "sourceName": self.source.name},
                )
            )
        return items

