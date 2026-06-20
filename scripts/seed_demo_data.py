from __future__ import annotations

import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import storage  # noqa: E402
from app.collectors.fixtures import FixtureCollector  # noqa: E402
from app.keywords import load_keywords  # noqa: E402
from app.schemas import utc_now  # noqa: E402
from app.sources import SOURCES  # noqa: E402


def main() -> None:
    storage.initialize_database()
    keywords = load_keywords()
    for source in SOURCES:
        started_at = utc_now()
        started = time.perf_counter()
        collector = FixtureCollector(source)
        items = collector.fetch()
        with storage.get_connection() as conn:
            run_id = storage.create_fetch_run(
                conn,
                source=source.id,
                trigger="seed_demo",
                started_at=started_at,
            )
            saved = storage.save_hot_items(conn, items=items, keywords=keywords)
            storage.finish_fetch_run(
                conn,
                run_id=run_id,
                source=source.id,
                status="success",
                duration_ms=(time.perf_counter() - started) * 1000,
                items_count=saved,
            )
    print(f"Seeded demo data for {len(SOURCES)} sources into data/hotspots.sqlite")


if __name__ == "__main__":
    main()

