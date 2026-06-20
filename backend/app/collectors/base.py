from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..schemas import HotItem
from ..sources import SourceConfig


@dataclass
class CollectorError(Exception):
    message: str
    error_type: str = "CollectorError"
    http_status: int | None = None
    request_url: str | None = None
    response_snippet: str | None = None

    def __str__(self) -> str:
        return self.message


class Collector(Protocol):
    source: SourceConfig

    def fetch(self) -> list[HotItem]:
        raise NotImplementedError

