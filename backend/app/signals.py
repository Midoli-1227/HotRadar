from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import HotItem
from .settings import SIGNAL_RULES_PATH


DEFAULT_ENABLED_SOURCES = {
    "openai",
    "anthropic",
    "google",
    "microsoft",
    "nvidia",
    "intel",
}


@dataclass(frozen=True)
class SignalRule:
    term: str
    weight: int
    kind: str


@dataclass(frozen=True)
class SignalRules:
    enabled_sources: set[str]
    hide_low_signal_on_dashboard: bool
    high_threshold: int
    medium_threshold: int
    rules: list[SignalRule]


DEFAULT_RULES = SignalRules(
    enabled_sources=DEFAULT_ENABLED_SOURCES,
    hide_low_signal_on_dashboard=True,
    high_threshold=4,
    medium_threshold=1,
    rules=[
        SignalRule("api", 4, "high"),
        SignalRule("pricing", 5, "high"),
        SignalRule("model", 4, "high"),
        SignalRule("release", 3, "high"),
        SignalRule("launch", 3, "high"),
        SignalRule("customer story", -4, "low"),
        SignalRule("case study", -4, "low"),
        SignalRule("webinar", -3, "low"),
        SignalRule("empowering", -3, "low"),
        SignalRule("celebrating", -3, "low"),
    ],
)


def _rule_entries(raw: Any, kind: str) -> list[SignalRule]:
    entries: list[SignalRule] = []
    if not isinstance(raw, list):
        return entries

    for item in raw:
        if isinstance(item, str):
            term = item.strip()
            weight = 1 if kind == "high" else -1
        elif isinstance(item, dict):
            term = str(item.get("term") or "").strip()
            try:
                weight = int(item.get("weight", 1 if kind == "high" else -1))
            except (TypeError, ValueError):
                weight = 1 if kind == "high" else -1
        else:
            continue

        if term:
            entries.append(SignalRule(term=term, weight=weight, kind=kind))
    return entries


def load_signal_rules(path: Path = SIGNAL_RULES_PATH) -> SignalRules:
    if not path.exists():
        return DEFAULT_RULES

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_RULES

    enabled = payload.get("enabledSources", list(DEFAULT_ENABLED_SOURCES))
    enabled_sources = {str(source).strip() for source in enabled if str(source).strip()} if isinstance(enabled, list) else DEFAULT_ENABLED_SOURCES
    high_threshold = int(payload.get("highThreshold", DEFAULT_RULES.high_threshold))
    medium_threshold = int(payload.get("mediumThreshold", DEFAULT_RULES.medium_threshold))
    high_rules = _rule_entries(payload.get("highSignal"), "high")
    low_rules = _rule_entries(payload.get("lowSignal"), "low")

    return SignalRules(
        enabled_sources=enabled_sources or DEFAULT_ENABLED_SOURCES,
        hide_low_signal_on_dashboard=bool(payload.get("hideLowSignalOnDashboard", True)),
        high_threshold=high_threshold,
        medium_threshold=medium_threshold,
        rules=high_rules + low_rules or DEFAULT_RULES.rules,
    )


def signal_text_for_item(item: HotItem) -> str:
    parts = [
        item.title,
        item.summary or "",
        item.heat or "",
        item.author or "",
    ]
    for value in item.extra.values():
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
        elif isinstance(value, list):
            parts.extend(str(entry) for entry in value if isinstance(entry, (str, int, float)))
    return " ".join(parts)


def _matches_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._+/#-]*", term):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(term.lower())}(?![A-Za-z0-9])", text.lower()) is not None
    return term in text


def score_item(item: HotItem, rules: SignalRules) -> dict[str, Any]:
    if item.source not in rules.enabled_sources:
        return {}

    text = signal_text_for_item(item)
    score = 0
    reasons: list[dict[str, Any]] = []
    seen_terms: set[str] = set()

    for rule in rules.rules:
        term_key = rule.term.casefold()
        if term_key in seen_terms:
            continue
        if _matches_term(text, rule.term):
            seen_terms.add(term_key)
            score += rule.weight
            reasons.append({"term": rule.term, "weight": rule.weight, "kind": rule.kind})

    if score >= rules.high_threshold:
        level = "high"
    elif score >= rules.medium_threshold:
        level = "medium"
    else:
        level = "low"

    return {
        "signalScore": score,
        "signalLevel": level,
        "signalReasons": reasons,
    }


def apply_signal_scores(items: list[HotItem], rules: SignalRules) -> list[HotItem]:
    for item in items:
        score = score_item(item, rules)
        if score:
            item.extra.update(score)
    return items


def is_low_signal_item(item: dict[str, Any]) -> bool:
    extra = item.get("extra")
    return isinstance(extra, dict) and extra.get("signalLevel") == "low"


def signal_sort_key(item: dict[str, Any]) -> tuple[int, int, int]:
    extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
    level = extra.get("signalLevel")
    level_priority = {"high": 0, "medium": 1, "low": 2}.get(str(level), 1)
    try:
        score = int(extra.get("signalScore", 0))
    except (TypeError, ValueError):
        score = 0
    rank = item.get("rank")
    rank_value = int(rank) if isinstance(rank, int) else 999999
    return (level_priority, -score, rank_value)
