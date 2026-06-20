from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import main, settings, storage  # noqa: E402
from app.schemas import HotItem  # noqa: E402


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "hotspots.sqlite"
        self.previous_db_path = main.service.db_path
        self.previous_require_admin = settings.REQUIRE_ADMIN_TOKEN
        self.previous_admin_token = settings.ADMIN_TOKEN
        self.previous_collector_mode = os.environ.get("HOTRADAR_COLLECTOR_MODE")

        os.environ["HOTRADAR_COLLECTOR_MODE"] = "fixture"
        settings.REQUIRE_ADMIN_TOKEN = False
        settings.ADMIN_TOKEN = ""
        main.service.db_path = self.db_path
        main.service.reset_runtime_state()
        storage.initialize_database(self.db_path)

    def tearDown(self) -> None:
        main.service.db_path = self.previous_db_path
        main.service.reset_runtime_state()
        settings.REQUIRE_ADMIN_TOKEN = self.previous_require_admin
        settings.ADMIN_TOKEN = self.previous_admin_token
        if self.previous_collector_mode is None:
            os.environ.pop("HOTRADAR_COLLECTOR_MODE", None)
        else:
            os.environ["HOTRADAR_COLLECTOR_MODE"] = self.previous_collector_mode
        self.tmp.cleanup()

    def test_health_dashboard_history_and_debug_endpoints(self) -> None:
        with TestClient(main.app) as client:
            health = client.get("/")
            dashboard = client.get("/api/dashboard")
            history = client.get("/api/history?limit=10")
            debug = client.get("/api/debug/sources")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("sections", dashboard.json())
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["pagination"]["limit"], 10)
        self.assertEqual(debug.status_code, 200)
        self.assertEqual(len(debug.json()["sources"]), 14)

    def test_manual_refresh_queues_fixture_collection_and_exposes_status(self) -> None:
        with TestClient(main.app) as client:
            response = client.post("/api/refresh")
            status_response = client.get("/api/refresh/status")

        payload = response.json()
        status_payload = status_response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["status"], "queued")
        self.assertTrue(payload["jobId"].startswith("refresh-"))
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_payload["latestJob"]["jobId"], payload["jobId"])
        self.assertIn(status_payload["latestJob"]["status"], {"completed", "running", "queued"})

    def test_refresh_queue_reuses_active_job_instead_of_creating_duplicate(self) -> None:
        accepted, first = main.service.queue_refresh(trigger="manual")
        duplicate_accepted, duplicate = main.service.queue_refresh(trigger="manual")

        self.assertTrue(accepted)
        self.assertFalse(duplicate_accepted)
        self.assertEqual(duplicate["jobId"], first["jobId"])
        self.assertEqual(duplicate["status"], "queued")

    def test_history_endpoint_uses_isolated_database_and_offset_pagination(self) -> None:
        with storage.get_connection(self.db_path) as conn:
            storage.save_hot_items(
                conn,
                items=[
                    HotItem(
                        source="openai",
                        section="AI / Big Tech",
                        title="API item one",
                        url="https://openai.com/news/api-one",
                        fetchedAt="2026-01-01T00:00:00+00:00",
                    ),
                    HotItem(
                        source="openai",
                        section="AI / Big Tech",
                        title="API item two",
                        url="https://openai.com/news/api-two",
                        fetchedAt="2026-01-01T00:01:00+00:00",
                    ),
                ],
                keywords=["API"],
            )

        with TestClient(main.app) as client:
            first = client.get("/api/history?q=API&limit=1&offset=0")
            second = client.get("/api/history?q=API&limit=1&offset=1")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["pagination"]["total"], 2)
        self.assertTrue(first.json()["pagination"]["hasMore"])
        self.assertEqual(first.json()["items"][0]["title"], "API item two")
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["pagination"]["hasMore"])
        self.assertEqual(second.json()["items"][0]["title"], "API item one")

    def test_admin_token_protects_operational_endpoints_when_required(self) -> None:
        settings.REQUIRE_ADMIN_TOKEN = True
        settings.ADMIN_TOKEN = "test-secret"

        with TestClient(main.app) as client:
            unauthorized = client.post("/api/refresh")
            authorized = client.post(
                "/api/refresh",
                headers={"X-HotRadar-Admin-Token": "test-secret"},
            )
            debug = client.get(
                "/api/debug/sources",
                headers={"Authorization": "Bearer test-secret"},
            )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertTrue(authorized.json()["accepted"])
        self.assertEqual(debug.status_code, 200)


if __name__ == "__main__":
    unittest.main()
