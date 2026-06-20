from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.keywords import match_keywords  # noqa: E402


class KeywordTests(unittest.TestCase):
    def test_matches_english_case_insensitive_and_chinese(self) -> None:
        matches = match_keywords(
            title="OpenAI ships a new 芯片 partnership",
            summary="半导体 supply chain and 美股 reaction",
            source="NVIDIA",
            extra={"tag": "Cloud"},
            keywords=["openai", "芯片", "美股", "cloud", "missing"],
        )

        self.assertEqual(matches, ["openai", "芯片", "美股", "cloud"])

    def test_deduplicates_keyword_matches(self) -> None:
        matches = match_keywords(
            title="AI AI AI",
            summary=None,
            source="OpenAI",
            keywords=["AI", "AI"],
        )

        self.assertEqual(matches, ["AI"])


if __name__ == "__main__":
    unittest.main()
