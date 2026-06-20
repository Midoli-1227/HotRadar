CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    section TEXT NOT NULL,
    display_type TEXT NOT NULL,
    homepage_url TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    refresh_interval_minutes INTEGER NOT NULL DEFAULT 30
);

CREATE TABLE IF NOT EXISTS hot_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    section TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    normalized_url TEXT,
    dedupe_key TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(source, dedupe_key)
);

CREATE TABLE IF NOT EXISTS hot_item_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES hot_items(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    rank INTEGER,
    heat TEXT,
    summary TEXT,
    author TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    matched_keywords TEXT NOT NULL DEFAULT '[]',
    extra_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS fetch_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms REAL,
    items_count INTEGER NOT NULL DEFAULT 0,
    trigger TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES fetch_runs(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    http_status INTEGER,
    request_url TEXT,
    response_snippet TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    last_success_at TEXT,
    last_fetch_at TEXT,
    last_failure_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    latest_error_type TEXT,
    latest_http_status INTEGER,
    latest_error_message TEXT,
    average_duration_ms REAL,
    latest_items_count INTEGER NOT NULL DEFAULT 0,
    last_run_trigger TEXT
);

CREATE INDEX IF NOT EXISTS idx_hot_items_source ON hot_items(source);
CREATE INDEX IF NOT EXISTS idx_hot_items_section ON hot_items(section);
CREATE INDEX IF NOT EXISTS idx_hot_items_last_seen ON hot_items(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_item ON hot_item_snapshots(item_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_source_fetched ON hot_item_snapshots(source, fetched_at);
CREATE INDEX IF NOT EXISTS idx_fetch_runs_source_started ON fetch_runs(source, started_at);
