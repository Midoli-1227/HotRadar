from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .keywords import match_keywords
from .schemas import HotItem, utc_now
from .settings import BASE_DIR, DATABASE_PATH, SIGNAL_RULES_PATH
from .signals import is_low_signal_item, load_signal_rules, signal_sort_key
from .sources import SOURCES, SECTION_MY_WATCH, THEME_ORDER, SourceConfig
from .url_utils import normalize_url


MIGRATIONS_DIR = BASE_DIR / "migrations"


@contextmanager
def get_connection(db_path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def list_migration_files(migrations_dir: Path = MIGRATIONS_DIR) -> list[tuple[int, Path]]:
    files: list[tuple[int, Path]] = []
    for path in sorted(migrations_dir.glob("*.sql")):
        version_text = path.name.split("_", 1)[0]
        if not version_text.isdigit():
            continue
        files.append((int(version_text), path))
    return files


def apply_migrations(
    conn: sqlite3.Connection,
    *,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> list[int]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        int(row["version"])
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    applied_now: list[int] = []
    for version, path in list_migration_files(migrations_dir):
        if version in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            """
            INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (?, ?, ?)
            """,
            (version, path.name, utc_now()),
        )
        applied_now.append(version)
    return applied_now


def get_applied_migrations(db_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT version, name, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
    return [
        {"version": row["version"], "name": row["name"], "appliedAt": row["applied_at"]}
        for row in rows
    ]


def initialize_database(db_path: Path = DATABASE_PATH) -> None:
    with get_connection(db_path) as conn:
        apply_migrations(conn)
        upsert_sources(conn, SOURCES)


def upsert_sources(conn: sqlite3.Connection, sources: list[SourceConfig]) -> None:
    active_ids = [source.id for source in sources]
    for source in sources:
        conn.execute(
            """
            INSERT INTO sources (
                id, name, section, display_type, homepage_url, enabled, refresh_interval_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                section = excluded.section,
                display_type = excluded.display_type,
                homepage_url = excluded.homepage_url,
                enabled = excluded.enabled,
                refresh_interval_minutes = excluded.refresh_interval_minutes
            """,
            (
                source.id,
                source.name,
                source.section,
                source.displayType,
                source.homepageUrl,
                1 if source.enabled else 0,
                source.refreshIntervalMinutes,
            ),
        )
        conn.execute(
            "INSERT OR IGNORE INTO source_status (source) VALUES (?)",
            (source.id,),
        )
    if active_ids:
        placeholders = ",".join("?" for _ in active_ids)
        conn.execute(
            f"UPDATE sources SET enabled = 0 WHERE id NOT IN ({placeholders})",
            active_ids,
        )


def create_fetch_run(
    conn: sqlite3.Connection,
    *,
    source: str,
    trigger: str,
    started_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO fetch_runs (source, status, started_at, trigger)
        VALUES (?, 'running', ?, ?)
        """,
        (source, started_at, trigger),
    )
    return int(cursor.lastrowid)


def _status_for_row(row: sqlite3.Row | None) -> str:
    if row is None or row["last_fetch_at"] is None:
        return "never_fetched"
    failures = int(row["consecutive_failures"] or 0)
    if failures == 0:
        return "success"
    if row["last_success_at"]:
        return "degraded"
    return "failed"


def _average_duration(previous: Any, duration_ms: float) -> float:
    if previous is None:
        return round(duration_ms, 2)
    return round(float(previous) * 0.7 + duration_ms * 0.3, 2)


def finish_fetch_run(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    source: str,
    status: str,
    duration_ms: float,
    items_count: int,
    error_type: str | None = None,
    error_message: str | None = None,
    http_status: int | None = None,
) -> None:
    finished_at = utc_now()
    run = conn.execute("SELECT trigger FROM fetch_runs WHERE id = ?", (run_id,)).fetchone()
    trigger = run["trigger"] if run else "unknown"

    conn.execute(
        """
        UPDATE fetch_runs
        SET status = ?, finished_at = ?, duration_ms = ?, items_count = ?
        WHERE id = ?
        """,
        (status, finished_at, duration_ms, items_count, run_id),
    )

    status_row = conn.execute(
        "SELECT * FROM source_status WHERE source = ?",
        (source,),
    ).fetchone()
    avg = _average_duration(status_row["average_duration_ms"] if status_row else None, duration_ms)

    if status == "success":
        conn.execute(
            """
            INSERT INTO source_status (
                source, last_success_at, last_fetch_at, consecutive_failures,
                latest_error_type, latest_http_status, latest_error_message,
                average_duration_ms, latest_items_count, last_run_trigger
            )
            VALUES (?, ?, ?, 0, NULL, NULL, NULL, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_success_at = excluded.last_success_at,
                last_fetch_at = excluded.last_fetch_at,
                consecutive_failures = 0,
                latest_error_type = NULL,
                latest_http_status = NULL,
                latest_error_message = NULL,
                average_duration_ms = excluded.average_duration_ms,
                latest_items_count = excluded.latest_items_count,
                last_run_trigger = excluded.last_run_trigger
            """,
            (source, finished_at, finished_at, avg, items_count, trigger),
        )
    else:
        previous_failures = int(status_row["consecutive_failures"] or 0) if status_row else 0
        conn.execute(
            """
            INSERT INTO source_status (
                source, last_fetch_at, last_failure_at, consecutive_failures,
                latest_error_type, latest_http_status, latest_error_message,
                average_duration_ms, latest_items_count, last_run_trigger
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_fetch_at = excluded.last_fetch_at,
                last_failure_at = excluded.last_failure_at,
                consecutive_failures = excluded.consecutive_failures,
                latest_error_type = excluded.latest_error_type,
                latest_http_status = excluded.latest_http_status,
                latest_error_message = excluded.latest_error_message,
                average_duration_ms = excluded.average_duration_ms,
                latest_items_count = excluded.latest_items_count,
                last_run_trigger = excluded.last_run_trigger
            """,
            (
                source,
                finished_at,
                finished_at,
                previous_failures + 1,
                error_type or "CollectorError",
                http_status,
                error_message or "Unknown collector failure",
                avg,
                items_count,
                trigger,
            ),
        )


def record_fetch_error(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    source: str,
    error_type: str,
    error_message: str,
    http_status: int | None = None,
    request_url: str | None = None,
    response_snippet: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO fetch_errors (
            run_id, source, error_type, error_message, http_status,
            request_url, response_snippet, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            source,
            error_type,
            error_message[:2000],
            http_status,
            request_url,
            response_snippet[:2000] if response_snippet else None,
            utc_now(),
        ),
    )


def _dedupe_key_for_item(item: HotItem) -> tuple[str, str]:
    normalized = normalize_url(item.url)
    if normalized:
        return normalized, normalized
    return "", item.title.strip().casefold()


def save_hot_items(
    conn: sqlite3.Connection,
    *,
    items: list[HotItem],
    keywords: list[str],
) -> int:
    saved = 0
    for item in items:
        title = item.title.strip()
        if not title:
            continue

        normalized_url, dedupe_key = _dedupe_key_for_item(item)
        fetched_at = item.fetchedAt or utc_now()
        matched = match_keywords(
            title=title,
            summary=item.summary,
            source=item.source,
            extra=item.extra,
            keywords=keywords,
        )
        item.matchedKeywords = matched

        conn.execute(
            """
            INSERT INTO hot_items (
                source, section, title, url, normalized_url, dedupe_key,
                first_seen_at, last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, dedupe_key) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                normalized_url = excluded.normalized_url,
                section = excluded.section,
                last_seen_at = excluded.last_seen_at
            """,
            (
                item.source,
                item.section,
                title,
                item.url,
                normalized_url,
                dedupe_key,
                fetched_at,
                fetched_at,
            ),
        )
        item_row = conn.execute(
            "SELECT id FROM hot_items WHERE source = ? AND dedupe_key = ?",
            (item.source, dedupe_key),
        ).fetchone()
        if not item_row:
            continue

        conn.execute(
            """
            INSERT INTO hot_item_snapshots (
                item_id, source, rank, heat, summary, author, published_at,
                fetched_at, matched_keywords, extra_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_row["id"],
                item.source,
                item.rank,
                item.heat,
                item.summary,
                item.author,
                item.publishedAt,
                fetched_at,
                json.dumps(matched, ensure_ascii=False),
                json.dumps(item.extra, ensure_ascii=False),
            ),
        )
        saved += 1
    return saved


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _item_from_row(row: sqlite3.Row, source_name: str | None = None) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source": row["source"],
        "sourceName": source_name or row["source"],
        "section": row["section"],
        "title": row["title"],
        "url": row["url"],
        "rank": row["rank"],
        "heat": row["heat"],
        "summary": row["summary"],
        "author": row["author"],
        "publishedAt": row["published_at"],
        "fetchedAt": row["fetched_at"],
        "matchedKeywords": _json_list(row["matched_keywords"]),
        "extra": _json_object(row["extra_json"]),
    }


def get_latest_items_for_source(
    conn: sqlite3.Connection,
    *,
    source: str,
    source_name: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        WITH latest_batch AS (
            SELECT MAX(fetched_at) AS fetched_at
            FROM hot_item_snapshots
            WHERE source = ?
        ),
        batch AS (
            SELECT *
            FROM hot_item_snapshots
            WHERE source = ?
              AND fetched_at = (SELECT fetched_at FROM latest_batch)
        ),
        latest AS (
            SELECT item_id, MAX(id) AS snapshot_id
            FROM batch
            GROUP BY item_id
        )
        SELECT
            hi.id,
            hi.source,
            hi.section,
            hi.title,
            hi.url,
            hs.rank,
            hs.heat,
            hs.summary,
            hs.author,
            hs.published_at,
            hs.fetched_at,
            hs.matched_keywords,
            hs.extra_json
        FROM latest
        JOIN hot_items hi ON hi.id = latest.item_id
        JOIN hot_item_snapshots hs ON hs.id = latest.snapshot_id
        ORDER BY
            CASE WHEN hs.rank IS NULL THEN 999999 ELSE hs.rank END ASC,
            hs.id ASC
        LIMIT ?
        """,
        (source, source, limit),
    ).fetchall()

    if rows:
        return [_item_from_row(row, source_name) for row in rows]

    rows = conn.execute(
        """
        WITH latest AS (
            SELECT item_id, MAX(id) AS snapshot_id
            FROM hot_item_snapshots
            WHERE source = ?
            GROUP BY item_id
        )
        SELECT
            hi.id,
            hi.source,
            hi.section,
            hi.title,
            hi.url,
            hs.rank,
            hs.heat,
            hs.summary,
            hs.author,
            hs.published_at,
            hs.fetched_at,
            hs.matched_keywords,
            hs.extra_json
        FROM latest
        JOIN hot_items hi ON hi.id = latest.item_id
        JOIN hot_item_snapshots hs ON hs.id = latest.snapshot_id
        ORDER BY
            CASE WHEN hs.rank IS NULL THEN 999999 ELSE hs.rank END ASC,
            hs.fetched_at DESC,
            hi.last_seen_at DESC
        LIMIT ?
        """,
        (source, limit),
    ).fetchall()
    return [_item_from_row(row, source_name) for row in rows]


def get_dashboard_data(db_path: Path = DATABASE_PATH) -> dict[str, Any]:
    initialize_database(db_path)
    signal_rules = load_signal_rules(SIGNAL_RULES_PATH)
    with get_connection(db_path) as conn:
        status_rows = {
            row["source"]: row
            for row in conn.execute(
                """
                SELECT st.*
                FROM source_status st
                JOIN sources s ON s.id = st.source
                WHERE s.enabled = 1
                """
            ).fetchall()
        }
        sections: list[dict[str, Any]] = []
        my_watch: list[dict[str, Any]] = []
        seen_watch_keys: set[str] = set()

        for section_name in THEME_ORDER:
            if section_name == SECTION_MY_WATCH:
                continue

            panels = []
            for source in [item for item in SOURCES if item.section == section_name and item.enabled]:
                status = status_rows.get(source.id)
                items = get_latest_items_for_source(
                    conn,
                    source=source.id,
                    source_name=source.name,
                    limit=20,
                )
                hidden_low_signal_count = 0
                signal_enabled = source.id in signal_rules.enabled_sources
                if signal_enabled:
                    hidden_low_signal_count = sum(1 for item in items if is_low_signal_item(item))
                    if signal_rules.hide_low_signal_on_dashboard:
                        items = [item for item in items if not is_low_signal_item(item)]
                    items = sorted(items, key=signal_sort_key)

                for item in items:
                    if item["matchedKeywords"]:
                        key = f"{item['source']}::{item['url'] or item['title']}"
                        if key not in seen_watch_keys:
                            seen_watch_keys.add(key)
                            my_watch.append(item)

                panel = {
                    "id": source.id,
                    "name": source.name,
                    "section": source.section,
                    "displayType": source.displayType,
                    "homepageUrl": source.homepageUrl,
                    "lastSuccessAt": status["last_success_at"] if status else None,
                    "lastFetchAt": status["last_fetch_at"] if status else None,
                    "currentStatus": _status_for_row(status),
                    "items": items,
                }
                if signal_enabled:
                    panel["hiddenLowSignalCount"] = hidden_low_signal_count
                panels.append(panel)

            sections.append({"id": section_name, "title": section_name, "sources": panels})

        my_watch.sort(key=lambda item: item.get("fetchedAt") or "", reverse=True)
        last_refresh = None
        for status in status_rows.values():
            candidate = status["last_fetch_at"]
            if candidate and (last_refresh is None or candidate > last_refresh):
                last_refresh = candidate

        return {
            "generatedAt": utc_now(),
            "lastRefreshAt": last_refresh,
            "myWatch": {
                "id": "my-watch",
                "title": SECTION_MY_WATCH,
                "items": my_watch[:50],
            },
            "sections": sections,
        }


def get_history(
    *,
    q: str | None = None,
    source: str | None = None,
    section: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    initialize_database(db_path)
    where = ["1 = 1"]
    params: list[Any] = []

    if q:
        like = f"%{q}%"
        where.append("(hi.title LIKE ? OR hs.summary LIKE ? OR hs.matched_keywords LIKE ?)")
        params.extend([like, like, like])
    if source:
        where.append("hi.source = ?")
        params.append(source)
    if section:
        where.append("hi.section = ?")
        params.append(section)
    if start:
        where.append("hs.fetched_at >= ?")
        params.append(start)
    if end:
        where.append("hs.fetched_at <= ?")
        params.append(end)

    filtered_sql = f"""
        WITH filtered AS (
            SELECT hi.id AS item_id
            FROM hot_items hi
            JOIN hot_item_snapshots hs ON hs.item_id = hi.id
            JOIN sources s ON s.id = hi.source AND s.enabled = 1
            WHERE {' AND '.join(where)}
            GROUP BY hi.id
        )
    """
    count_sql = f"""
        {filtered_sql}
        SELECT COUNT(*) AS total
        FROM filtered
    """
    sql = f"""
        {filtered_sql}
        SELECT
            hi.id,
            hi.source,
            s.name AS source_name,
            hi.section,
            hi.title,
            hi.url,
            hi.first_seen_at,
            hi.last_seen_at,
            COUNT(hs.id) AS seen_count,
            (
                SELECT rank FROM hot_item_snapshots
                WHERE item_id = hi.id
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
            ) AS latest_rank,
            (
                SELECT heat FROM hot_item_snapshots
                WHERE item_id = hi.id
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
            ) AS latest_heat
        FROM hot_items hi
        JOIN filtered ON filtered.item_id = hi.id
        JOIN hot_item_snapshots hs ON hs.item_id = hi.id
        JOIN sources s ON s.id = hi.source AND s.enabled = 1
        GROUP BY hi.id
        ORDER BY hi.last_seen_at DESC
        LIMIT ?
        OFFSET ?
    """

    with get_connection(db_path) as conn:
        total = int(conn.execute(count_sql, params).fetchone()["total"])
        rows = conn.execute(sql, [*params, limit, offset]).fetchall()
    return {
        "items": [
            {
                "id": row["id"],
                "title": row["title"],
                "source": row["source"],
                "sourceName": row["source_name"] or row["source"],
                "section": row["section"],
                "firstSeenAt": row["first_seen_at"],
                "lastSeenAt": row["last_seen_at"],
                "seenCount": row["seen_count"],
                "latestRank": row["latest_rank"],
                "latestHeat": row["latest_heat"],
                "url": row["url"],
            }
            for row in rows
        ],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "hasMore": offset + len(rows) < total,
        },
    }


def get_source_status_rows(db_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.name,
                s.section,
                s.display_type,
                s.homepage_url,
                st.last_fetch_at,
                st.last_success_at,
                st.last_failure_at,
                st.consecutive_failures,
                st.latest_error_type,
                st.latest_http_status,
                st.latest_error_message,
                st.average_duration_ms,
                st.latest_items_count,
                st.last_run_trigger
            FROM sources s
            LEFT JOIN source_status st ON st.source = s.id
            WHERE s.enabled = 1
            ORDER BY s.section, s.name
            """
        ).fetchall()

    status_priority = {"failed": 0, "degraded": 1, "never_fetched": 2, "success": 3}
    payload = []
    for row in rows:
        current = _status_for_row(row)
        payload.append(
            {
                "id": row["id"],
                "name": row["name"],
                "section": row["section"],
                "displayType": row["display_type"],
                "homepageUrl": row["homepage_url"],
                "lastFetchAt": row["last_fetch_at"],
                "lastSuccessAt": row["last_success_at"],
                "lastFailureAt": row["last_failure_at"],
                "currentStatus": current,
                "itemsFetched": row["latest_items_count"] or 0,
                "consecutiveFailures": row["consecutive_failures"] or 0,
                "latestErrorType": row["latest_error_type"],
                "latestHttpStatus": row["latest_http_status"],
                "latestErrorMessage": row["latest_error_message"],
                "averageDurationMs": row["average_duration_ms"],
                "lastRunTrigger": row["last_run_trigger"],
                "_priority": status_priority[current],
            }
        )
    payload.sort(key=lambda item: (item.pop("_priority"), item["section"], item["name"]))
    return payload


def recent_fetch_age_seconds(
    conn: sqlite3.Connection,
    *,
    source: str,
    now: datetime,
) -> float | None:
    row = conn.execute(
        "SELECT last_fetch_at FROM source_status WHERE source = ?",
        (source,),
    ).fetchone()
    if not row or not row["last_fetch_at"]:
        return None
    try:
        last_fetch = datetime.fromisoformat(row["last_fetch_at"])
    except ValueError:
        return None
    return (now - last_fetch).total_seconds()
