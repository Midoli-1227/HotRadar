from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class HotItem:
    source: str
    section: str
    title: str
    url: str = ""
    rank: int | None = None
    heat: str | None = None
    summary: str | None = None
    author: str | None = None
    publishedAt: str | None = None
    fetchedAt: str = field(default_factory=utc_now)
    mobileUrl: str | None = None
    matchedKeywords: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "section": self.section,
            "title": self.title,
            "url": self.url,
            "rank": self.rank,
            "heat": self.heat,
            "summary": self.summary,
            "author": self.author,
            "publishedAt": self.publishedAt,
            "fetchedAt": self.fetchedAt,
            "mobileUrl": self.mobileUrl,
            "matchedKeywords": self.matchedKeywords,
            "extra": self.extra,
        }

