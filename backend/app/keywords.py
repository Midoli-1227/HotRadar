from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .settings import WATCH_KEYWORDS_PATH

logger = logging.getLogger("hotradar.keywords")

DEFAULT_KEYWORDS = [
    "AI",
    "OpenAI",
    "Anthropic",
    "Google",
    "Cloud",
    "Gemini",
    "ChatGPT",
    "NVIDIA",
    "半导体",
    "芯片",
    "美股",
    "美联储",
    "纳斯达克",
    "标普500",
]


def ensure_keywords_file(path: Path = WATCH_KEYWORDS_PATH) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"keywords": DEFAULT_KEYWORDS}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_keywords(path: Path = WATCH_KEYWORDS_PATH) -> list[str]:
    ensure_keywords_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Invalid keyword config JSON at %s: %s", path, exc)
        return DEFAULT_KEYWORDS.copy()
    except OSError as exc:
        logger.error("Cannot read keyword config at %s: %s", path, exc)
        return DEFAULT_KEYWORDS.copy()

    keywords = payload.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
        logger.error("Keyword config must be an object with a string array named 'keywords'.")
        return DEFAULT_KEYWORDS.copy()

    return [keyword.strip() for keyword in keywords if keyword.strip()]


def _metadata_text(extra: dict[str, Any] | None) -> str:
    if not extra:
        return ""
    values: list[str] = []
    for value in extra.values():
        if isinstance(value, (str, int, float)):
            values.append(str(value))
        elif isinstance(value, list):
            values.extend(str(item) for item in value if isinstance(item, (str, int, float)))
    return " ".join(values)


def match_keywords(
    *,
    title: str,
    summary: str | None,
    source: str,
    extra: dict[str, Any] | None = None,
    keywords: list[str] | None = None,
) -> list[str]:
    active_keywords = keywords if keywords is not None else load_keywords()
    haystack = " ".join([title or "", summary or "", source or "", _metadata_text(extra)])
    folded = haystack.casefold()

    matches: list[str] = []
    for keyword in active_keywords:
        needle = keyword.strip()
        if not needle:
            continue
        if needle.casefold() in folded and needle not in matches:
            matches.append(needle)
    return matches

