from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import storage  # noqa: E402
from app.schemas import HotItem  # noqa: E402


class StorageTests(unittest.TestCase):
    def test_dedupes_by_normalized_url_and_keeps_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            item = HotItem(
                source="openai",
                section="AI / Big Tech",
                title="OpenAI update",
                url="https://openai.com/news/?utm_source=test&b=2&a=1#fragment",
                rank=1,
            )
            same = HotItem(
                source="openai",
                section="AI / Big Tech",
                title="OpenAI update",
                url="https://openai.com/news/?a=1&b=2",
                rank=2,
            )

            with storage.get_connection(db_path) as conn:
                storage.save_hot_items(conn, items=[item], keywords=["OpenAI"])
                storage.save_hot_items(conn, items=[same], keywords=["OpenAI"])
                item_count = conn.execute("SELECT COUNT(*) AS c FROM hot_items").fetchone()["c"]
                snapshot_count = conn.execute(
                    "SELECT COUNT(*) AS c FROM hot_item_snapshots"
                ).fetchone()["c"]

            self.assertEqual(item_count, 1)
            self.assertEqual(snapshot_count, 2)

            history = storage.get_history(q="OpenAI", db_path=db_path)
            self.assertEqual(history["items"][0]["seenCount"], 2)

    def test_dashboard_contains_all_source_panels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            dashboard = storage.get_dashboard_data(db_path)
            panel_count = sum(len(section["sources"]) for section in dashboard["sections"])

            self.assertEqual(panel_count, 14)

    def test_disabled_legacy_source_is_hidden_from_status_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sources (
                        id, name, section, display_type, homepage_url, enabled, refresh_interval_minutes
                    )
                    VALUES ('xueqiu', '雪球', 'Market / Finance', 'ranking', 'https://xueqiu.com/', 1, 30)
                    """
                )
                conn.execute("INSERT INTO source_status (source, last_fetch_at) VALUES ('xueqiu', ?)", ("2026-01-01T00:00:00+00:00",))
                storage.save_hot_items(
                    conn,
                    items=[
                        HotItem(
                            source="xueqiu",
                            section="Market / Finance",
                            title="Legacy xueqiu item",
                            url="https://xueqiu.com/status/1",
                        )
                    ],
                    keywords=[],
                )

            status_ids = [row["id"] for row in storage.get_source_status_rows(db_path)]
            history_sources = [item["source"] for item in storage.get_history(db_path=db_path)["items"]]

            self.assertNotIn("xueqiu", status_ids)
            self.assertNotIn("xueqiu", history_sources)

            with storage.get_connection(db_path) as conn:
                enabled = conn.execute("SELECT enabled FROM sources WHERE id = 'xueqiu'").fetchone()["enabled"]
            self.assertEqual(enabled, 0)

    def test_failed_fetch_keeps_previous_success_data_for_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                item = HotItem(
                    source="openai",
                    section="AI / Big Tech",
                    title="OpenAI cached item",
                    url="https://openai.com/news/cached",
                )
                saved = storage.save_hot_items(conn, items=[item], keywords=["OpenAI"])
                success_run = storage.create_fetch_run(
                    conn,
                    source="openai",
                    trigger="manual",
                    started_at=item.fetchedAt,
                )
                storage.finish_fetch_run(
                    conn,
                    run_id=success_run,
                    source="openai",
                    status="success",
                    duration_ms=12,
                    items_count=saved,
                )

                failed_run = storage.create_fetch_run(
                    conn,
                    source="openai",
                    trigger="manual",
                    started_at=item.fetchedAt,
                )
                storage.record_fetch_error(
                    conn,
                    run_id=failed_run,
                    source="openai",
                    error_type="NetworkError",
                    error_message="temporary failure",
                )
                storage.finish_fetch_run(
                    conn,
                    run_id=failed_run,
                    source="openai",
                    status="failed",
                    duration_ms=8,
                    items_count=0,
                    error_type="NetworkError",
                    error_message="temporary failure",
                )

            dashboard = storage.get_dashboard_data(db_path)
            openai_panel = next(
                panel
                for section in dashboard["sections"]
                for panel in section["sources"]
                if panel["id"] == "openai"
            )
            debug_row = next(row for row in storage.get_source_status_rows(db_path) if row["id"] == "openai")

            self.assertEqual(openai_panel["currentStatus"], "degraded")
            self.assertEqual(openai_panel["items"][0]["title"], "OpenAI cached item")
            self.assertEqual(debug_row["latestErrorType"], "NetworkError")

    def test_dashboard_uses_latest_source_batch_not_stale_ranked_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                old_item = HotItem(
                    source="wallstreetcn",
                    section="Market / Finance",
                    title="Old low-rank live item",
                    url="https://wallstreetcn.com/livenews/old",
                    rank=1,
                    fetchedAt="2026-01-01T00:00:00+00:00",
                )
                new_items = [
                    HotItem(
                        source="wallstreetcn",
                        section="Market / Finance",
                        title="New live item A",
                        url="https://wallstreetcn.com/livenews/new-a",
                        rank=4,
                        fetchedAt="2026-01-01T00:30:00+00:00",
                    ),
                    HotItem(
                        source="wallstreetcn",
                        section="Market / Finance",
                        title="New live item B",
                        url="https://wallstreetcn.com/livenews/new-b",
                        rank=19,
                        fetchedAt="2026-01-01T00:30:00+00:00",
                    ),
                ]
                storage.save_hot_items(conn, items=[old_item], keywords=[])
                storage.save_hot_items(conn, items=new_items, keywords=[])

            dashboard = storage.get_dashboard_data(db_path)
            panel = next(
                panel
                for section in dashboard["sections"]
                for panel in section["sources"]
                if panel["id"] == "wallstreetcn"
            )

            self.assertEqual([item["title"] for item in panel["items"]], ["New live item A", "New live item B"])

    def test_keyword_matches_do_not_reorder_ranked_source_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                storage.save_hot_items(
                    conn,
                    items=[
                        HotItem(
                            source="hacker-news",
                            section="Tech / Startup",
                            title="Official rank one story",
                            url="https://news.ycombinator.com/item?id=1",
                            rank=1,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                        ),
                        HotItem(
                            source="hacker-news",
                            section="Tech / Startup",
                            title="Official rank two AI story",
                            url="https://news.ycombinator.com/item?id=2",
                            rank=2,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                        ),
                    ],
                    keywords=["AI"],
                )

            dashboard = storage.get_dashboard_data(db_path)
            panel = next(
                panel
                for section in dashboard["sections"]
                for panel in section["sources"]
                if panel["id"] == "hacker-news"
            )

            self.assertEqual([item["title"] for item in panel["items"][:2]], ["Official rank one story", "Official rank two AI story"])
            self.assertEqual(panel["items"][0]["matchedKeywords"], [])
            self.assertEqual(panel["items"][1]["matchedKeywords"], ["AI"])

    def test_dashboard_prioritizes_signal_for_official_ai_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                storage.save_hot_items(
                    conn,
                    items=[
                        HotItem(
                            source="openai",
                            section="AI / Big Tech",
                            title="Low value customer story",
                            url="https://openai.com/news/low",
                            rank=1,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                            extra={"signalLevel": "low", "signalScore": -4},
                        ),
                        HotItem(
                            source="openai",
                            section="AI / Big Tech",
                            title="Medium platform update",
                            url="https://openai.com/news/medium",
                            rank=2,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                            extra={"signalLevel": "medium", "signalScore": 2},
                        ),
                        HotItem(
                            source="openai",
                            section="AI / Big Tech",
                            title="High signal API pricing release",
                            url="https://openai.com/news/high",
                            rank=3,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                            extra={"signalLevel": "high", "signalScore": 9},
                        ),
                    ],
                    keywords=[],
                )

            dashboard = storage.get_dashboard_data(db_path)
            panel = next(
                panel
                for section in dashboard["sections"]
                for panel in section["sources"]
                if panel["id"] == "openai"
            )

            self.assertEqual(panel["hiddenLowSignalCount"], 1)
            self.assertEqual(
                [item["title"] for item in panel["items"]],
                ["High signal API pricing release", "Medium platform update"],
            )

    def test_signal_metadata_does_not_reorder_ranking_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                storage.save_hot_items(
                    conn,
                    items=[
                        HotItem(
                            source="hacker-news",
                            section="Tech / Startup",
                            title="Official rank one low signal story",
                            url="https://news.ycombinator.com/item?id=10",
                            rank=1,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                            extra={"signalLevel": "low", "signalScore": -4},
                        ),
                        HotItem(
                            source="hacker-news",
                            section="Tech / Startup",
                            title="Official rank two high signal story",
                            url="https://news.ycombinator.com/item?id=20",
                            rank=2,
                            fetchedAt="2026-01-01T00:00:00+00:00",
                            extra={"signalLevel": "high", "signalScore": 9},
                        ),
                    ],
                    keywords=[],
                )

            dashboard = storage.get_dashboard_data(db_path)
            panel = next(
                panel
                for section in dashboard["sections"]
                for panel in section["sources"]
                if panel["id"] == "hacker-news"
            )

            self.assertNotIn("hiddenLowSignalCount", panel)
            self.assertEqual(
                [item["title"] for item in panel["items"][:2]],
                ["Official rank one low signal story", "Official rank two high signal story"],
            )

    def test_initialize_database_records_schema_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            migrations = storage.get_applied_migrations(db_path)

            self.assertEqual([item["version"] for item in migrations], [1])
            self.assertEqual(migrations[0]["name"], "001_initial_schema.sql")

    def test_history_supports_offset_pagination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "hotspots.sqlite"
            storage.initialize_database(db_path)

            with storage.get_connection(db_path) as conn:
                for index in range(3):
                    storage.save_hot_items(
                        conn,
                        items=[
                            HotItem(
                                source="openai",
                                section="AI / Big Tech",
                                title=f"OpenAI paged item {index}",
                                url=f"https://openai.com/news/paged-{index}",
                                fetchedAt=f"2026-01-01T00:0{index}:00+00:00",
                            )
                        ],
                        keywords=["OpenAI"],
                    )

            first = storage.get_history(q="OpenAI", limit=2, offset=0, db_path=db_path)
            second = storage.get_history(q="OpenAI", limit=2, offset=2, db_path=db_path)

            self.assertEqual(first["pagination"]["total"], 3)
            self.assertTrue(first["pagination"]["hasMore"])
            self.assertEqual([item["title"] for item in first["items"]], ["OpenAI paged item 2", "OpenAI paged item 1"])
            self.assertEqual([item["title"] for item in second["items"]], ["OpenAI paged item 0"])
            self.assertFalse(second["pagination"]["hasMore"])


if __name__ == "__main__":
    unittest.main()
