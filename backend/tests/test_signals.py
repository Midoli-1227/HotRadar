from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import HotItem  # noqa: E402
from app.signals import SignalRule, SignalRules, apply_signal_scores, score_item  # noqa: E402


class SignalTests(unittest.TestCase):
    def test_high_signal_terms_raise_score_and_level(self) -> None:
        rules = SignalRules(
            enabled_sources={"openai"},
            hide_low_signal_on_dashboard=True,
            high_threshold=4,
            medium_threshold=1,
            rules=[
                SignalRule("api", 4, "high"),
                SignalRule("pricing", 5, "high"),
                SignalRule("customer story", -4, "low"),
            ],
        )
        item = HotItem(
            source="openai",
            section="AI / Big Tech",
            title="OpenAI API pricing update",
            summary="A platform change for developers.",
        )

        score = score_item(item, rules)

        self.assertEqual(score["signalLevel"], "high")
        self.assertEqual(score["signalScore"], 9)
        self.assertEqual([reason["term"] for reason in score["signalReasons"]], ["api", "pricing"])

    def test_low_signal_terms_lower_score_but_high_terms_can_offset(self) -> None:
        rules = SignalRules(
            enabled_sources={"microsoft"},
            hide_low_signal_on_dashboard=True,
            high_threshold=4,
            medium_threshold=1,
            rules=[
                SignalRule("security", 4, "high"),
                SignalRule("customer story", -4, "low"),
            ],
        )
        item = HotItem(
            source="microsoft",
            section="AI / Big Tech",
            title="Customer story about a security release",
        )

        score = score_item(item, rules)

        self.assertEqual(score["signalLevel"], "low")
        self.assertEqual(score["signalScore"], 0)
        self.assertEqual([reason["term"] for reason in score["signalReasons"]], ["security", "customer story"])

    def test_ranking_sources_are_not_scored(self) -> None:
        rules = SignalRules(
            enabled_sources={"openai"},
            hide_low_signal_on_dashboard=True,
            high_threshold=4,
            medium_threshold=1,
            rules=[SignalRule("api", 4, "high")],
        )
        item = HotItem(
            source="hacker-news",
            section="Tech / Startup",
            title="A highly relevant API story",
        )

        self.assertEqual(score_item(item, rules), {})

    def test_apply_signal_scores_writes_to_extra(self) -> None:
        rules = SignalRules(
            enabled_sources={"google"},
            hide_low_signal_on_dashboard=True,
            high_threshold=4,
            medium_threshold=1,
            rules=[SignalRule("gemini", 4, "high")],
        )
        item = HotItem(
            source="google",
            section="AI / Big Tech",
            title="Gemini API update",
        )

        apply_signal_scores([item], rules)

        self.assertEqual(item.extra["signalLevel"], "high")
        self.assertEqual(item.extra["signalScore"], 4)


if __name__ == "__main__":
    unittest.main()
