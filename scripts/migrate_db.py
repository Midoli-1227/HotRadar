from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import storage  # noqa: E402
from app.settings import DATABASE_PATH  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply HotRadar SQLite migrations.")
    parser.add_argument(
        "--database",
        type=Path,
        default=DATABASE_PATH,
        help=f"SQLite path. Defaults to {DATABASE_PATH}.",
    )
    args = parser.parse_args()

    with storage.get_connection(args.database) as conn:
        applied_now = storage.apply_migrations(conn)
        storage.upsert_sources(conn, storage.SOURCES)

    migrations = storage.get_applied_migrations(args.database)
    if applied_now:
        print(f"Applied migrations: {', '.join(str(item) for item in applied_now)}")
    else:
        print("No pending migrations.")
    print("Current schema versions:")
    for migration in migrations:
        print(f"- {migration['version']}: {migration['name']} at {migration['appliedAt']}")


if __name__ == "__main__":
    main()
