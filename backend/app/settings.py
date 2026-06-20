from __future__ import annotations

import os
from pathlib import Path


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(os.getenv("HOTRADAR_CONFIG_DIR", str(BASE_DIR / "config")))
DATA_DIR = Path(os.getenv("HOTRADAR_DATA_DIR", str(BASE_DIR / "data")))

DATABASE_PATH = Path(os.getenv("HOTRADAR_DATABASE_PATH", str(DATA_DIR / "hotspots.sqlite")))
WATCH_KEYWORDS_PATH = Path(
    os.getenv("HOTRADAR_WATCH_KEYWORDS_PATH", str(CONFIG_DIR / "watch-keywords.json"))
)
SIGNAL_RULES_PATH = Path(
    os.getenv("HOTRADAR_SIGNAL_RULES_PATH", str(CONFIG_DIR / "signal-rules.json"))
)

HTTP_TIMEOUT_SECONDS = float(os.getenv("HOTRADAR_HTTP_TIMEOUT_SECONDS", "8"))
SCHEDULED_REFRESH_MINUTES = int(os.getenv("HOTRADAR_SCHEDULED_REFRESH_MINUTES", "30"))
MANUAL_REFRESH_COOLDOWN_SECONDS = int(
    os.getenv("HOTRADAR_MANUAL_REFRESH_COOLDOWN_SECONDS", "60")
)
SOURCE_MIN_REFRESH_SECONDS = int(os.getenv("HOTRADAR_SOURCE_MIN_REFRESH_SECONDS", "300"))
ENABLE_SCHEDULER = env_bool("HOTRADAR_ENABLE_SCHEDULER", True)

ADMIN_TOKEN = os.getenv("HOTRADAR_ADMIN_TOKEN", "")
REQUIRE_ADMIN_TOKEN = env_bool("HOTRADAR_REQUIRE_ADMIN_TOKEN", False)

LOG_LEVEL = os.getenv("HOTRADAR_LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("HOTRADAR_LOG_FORMAT", "json")
