from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.collectors.http import GitHubTrendingCollector, HackerNewsCollector, ProductHuntFeedCollector  # noqa: E402
from app.collectors.fixtures import FixtureCollector  # noqa: E402
from app.sources import DISPLAY_RANKING, SECTION_TECH_STARTUP, SOURCES, SourceConfig  # noqa: E402


class CollectorContractTests(unittest.TestCase):
    def test_fixture_collectors_return_normalized_items(self) -> None:
        for source in SOURCES:
            items = FixtureCollector(source).fetch()
            self.assertGreaterEqual(len(items), 5)
            first = items[0]
            self.assertEqual(first.source, source.id)
            self.assertEqual(first.section, source.section)
            self.assertTrue(first.title)
            self.assertTrue(first.url.startswith("http"))
            self.assertIsNotNone(first.fetchedAt)

    def test_hacker_news_uses_official_topstories_order(self) -> None:
        source = SourceConfig(
            "hacker-news",
            "Hacker News",
            SECTION_TECH_STARTUP,
            DISPLAY_RANKING,
            "https://news.ycombinator.com/",
        )
        responses = {
            HackerNewsCollector.topstories_url: [301, 302, 303],
            HackerNewsCollector.item_url_template.format(story_id=301): {
                "id": 301,
                "title": "First official story",
                "url": "https://example.com/first",
                "score": 90,
                "descendants": 10,
                "by": "alice",
                "time": 1760000000,
            },
            HackerNewsCollector.item_url_template.format(story_id=302): {
                "id": 302,
                "title": "Second official story",
                "score": 50,
                "descendants": 3,
                "by": "bob",
                "time": 1760000100,
            },
            HackerNewsCollector.item_url_template.format(story_id=303): {
                "id": 303,
                "title": "Third official story",
                "url": "https://example.com/third",
                "score": 20,
                "descendants": 0,
                "by": "carol",
                "time": 1760000200,
            },
        }

        with patch("app.collectors.http.fetch_json", side_effect=lambda url: responses[url]):
            items = HackerNewsCollector(source).fetch()

        self.assertEqual([item.rank for item in items], [1, 2, 3])
        self.assertEqual([item.title for item in items], ["First official story", "Second official story", "Third official story"])
        self.assertEqual(items[1].url, "https://news.ycombinator.com/item?id=302")

    def test_github_trending_uses_article_order_only(self) -> None:
        source = SourceConfig(
            "github-trending",
            "GitHub Trending",
            SECTION_TECH_STARTUP,
            DISPLAY_RANKING,
            "https://github.com/trending",
        )
        html = """
        <a href="/sponsors/explore">Sponsors</a>
        <article class="Box-row">
          <a href="/apps/pre-commit-ci">App link before heading</a>
          <h2 class="h3 lh-condensed"><a href="/owner-one/repo-one">owner-one / repo-one</a></h2>
        </article>
        <article class="Box-row">
          <h2 class="h3 lh-condensed"><a href="/owner-two/repo-two">owner-two / repo-two</a></h2>
        </article>
        """

        with patch("app.collectors.http.fetch_text", return_value=html):
            items = GitHubTrendingCollector(source).fetch()

        self.assertEqual([item.rank for item in items], [1, 2])
        self.assertEqual([item.title for item in items], ["owner-one/repo-one", "owner-two/repo-two"])

    def test_product_hunt_preserves_atom_entry_order(self) -> None:
        source = SourceConfig(
            "product-hunt",
            "Product Hunt",
            SECTION_TECH_STARTUP,
            DISPLAY_RANKING,
            "https://www.producthunt.com/",
        )
        feed = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>First Product</title>
            <link rel="alternate" type="text/html" href="https://www.producthunt.com/products/first"/>
            <summary>First tagline</summary>
            <published>2026-06-10T00:00:00Z</published>
          </entry>
          <entry>
            <title>Second Product</title>
            <link rel="alternate" type="text/html" href="https://www.producthunt.com/products/second"/>
            <summary>Second tagline</summary>
            <published>2026-06-10T00:01:00Z</published>
          </entry>
        </feed>
        """

        with patch("app.collectors.http.fetch_text", return_value=feed):
            items = ProductHuntFeedCollector(source).fetch()

        self.assertEqual([item.rank for item in items], [1, 2])
        self.assertEqual([item.title for item in items], ["First Product", "Second Product"])
        self.assertEqual([item.extra["orderSource"] for item in items], ["producthunt_atom_feed", "producthunt_atom_feed"])


if __name__ == "__main__":
    unittest.main()
