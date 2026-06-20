from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import storage
from .collectors import build_collectors
from .collectors.base import CollectorError
from .keywords import ensure_keywords_file, load_keywords
from .schemas import HotItem, utc_now
from .settings import (
    DATABASE_PATH,
    MANUAL_REFRESH_COOLDOWN_SECONDS,
    SIGNAL_RULES_PATH,
    SOURCE_MIN_REFRESH_SECONDS,
    WATCH_KEYWORDS_PATH,
)
from .signals import SignalRules, apply_signal_scores, load_signal_rules
from .sources import SOURCES

logger = logging.getLogger("hotradar.service")


class CollectionService:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._job_state_lock = threading.Lock()
        self._last_manual_refresh = 0.0
        self._latest_refresh_job: dict[str, Any] | None = None

    def bootstrap(self) -> None:
        ensure_keywords_file(WATCH_KEYWORDS_PATH)
        storage.initialize_database(self.db_path)

    def manual_refresh_allowed(self) -> tuple[bool, int]:
        with self._job_state_lock:
            now = time.time()
            elapsed = now - self._last_manual_refresh
            if elapsed < MANUAL_REFRESH_COOLDOWN_SECONDS:
                return False, int(MANUAL_REFRESH_COOLDOWN_SECONDS - elapsed)
            self._last_manual_refresh = now
            return True, 0

    def reset_runtime_state(self) -> None:
        with self._job_state_lock:
            self._last_manual_refresh = 0.0
            self._latest_refresh_job = None

    def queue_refresh(self, *, trigger: str, force: bool = False) -> tuple[bool, dict[str, Any]]:
        with self._job_state_lock:
            active = self._active_refresh_job_locked()
            if active:
                return False, dict(active)

            job = {
                "jobId": f"refresh-{uuid.uuid4().hex[:12]}",
                "status": "queued",
                "trigger": trigger,
                "force": force,
                "requestedAt": utc_now(),
                "startedAt": None,
                "finishedAt": None,
                "summary": None,
            }
            self._latest_refresh_job = job

        logger.info(
            "refresh job queued",
            extra={"event": "refresh_job_queued", "job_id": job["jobId"], "trigger": trigger},
        )
        return True, dict(job)

    def get_latest_refresh_job(self) -> dict[str, Any] | None:
        with self._job_state_lock:
            return dict(self._latest_refresh_job) if self._latest_refresh_job else None

    def get_active_refresh_job(self) -> dict[str, Any] | None:
        with self._job_state_lock:
            active = self._active_refresh_job_locked()
            return dict(active) if active else None

    def run_queued_refresh(self, job_id: str) -> dict[str, Any]:
        with self._job_state_lock:
            job = self._latest_refresh_job
            if not job or job["jobId"] != job_id:
                logger.warning(
                    "refresh job not found",
                    extra={"event": "refresh_job_missing", "job_id": job_id},
                )
                return {"status": "missing", "jobId": job_id}

            job["status"] = "running"
            job["startedAt"] = utc_now()
            trigger = str(job["trigger"])
            force = bool(job["force"])

        return self.refresh_all(trigger=trigger, force=force, job_id=job_id)

    def refresh_all(
        self,
        *,
        trigger: str,
        force: bool = False,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        started_at = utc_now()
        if not self._lock.acquire(blocking=False):
            summary = {
                "status": "already_running",
                "trigger": trigger,
                "startedAt": started_at,
                "finishedAt": utc_now(),
                "jobId": job_id,
                "sources": [],
            }
            self._finish_refresh_job(job_id=job_id, status="already_running", summary=summary)
            logger.info(
                "refresh job already running",
                extra={"event": "refresh_job_already_running", "job_id": job_id, "trigger": trigger},
            )
            return summary

        summary: dict[str, Any] = {
            "status": "completed",
            "trigger": trigger,
            "startedAt": started_at,
            "jobId": job_id,
            "sources": [],
        }
        try:
            logger.info(
                "refresh job started",
                extra={"event": "refresh_job_started", "job_id": job_id, "trigger": trigger},
            )
            self.bootstrap()
            collectors = build_collectors()
            keywords = load_keywords(WATCH_KEYWORDS_PATH)
            signal_rules = load_signal_rules(SIGNAL_RULES_PATH)
            now = datetime.now(UTC)

            for source in SOURCES:
                if not source.enabled:
                    continue

                age = self._recent_fetch_age_seconds(source.id, now)
                if not force and age is not None and age < SOURCE_MIN_REFRESH_SECONDS:
                    summary["sources"].append({"source": source.id, "status": "cached"})
                    logger.info(
                        "source refresh skipped because cached data is fresh",
                        extra={
                            "event": "source_refresh_cached_skip",
                            "job_id": job_id,
                            "source": source.id,
                            "age_seconds": round(age, 2),
                            "min_refresh_seconds": SOURCE_MIN_REFRESH_SECONDS,
                        },
                    )
                    continue

                collector = collectors[source.id]
                result = self._refresh_source(
                    collector=collector,
                    trigger=trigger,
                    keywords=keywords,
                    signal_rules=signal_rules,
                )
                summary["sources"].append(result)
        except Exception as exc:  # noqa: BLE001 - refresh jobs should leave inspectable state.
            summary["status"] = "failed"
            summary["errorType"] = exc.__class__.__name__
            summary["errorMessage"] = str(exc)
            logger.exception(
                "refresh job failed",
                extra={"event": "refresh_job_failed", "job_id": job_id, "trigger": trigger},
            )
        finally:
            self._lock.release()

        summary["finishedAt"] = utc_now()
        self._finish_refresh_job(job_id=job_id, status=summary["status"], summary=summary)
        logger.info(
            "refresh job finished",
            extra={
                "event": "refresh_job_finished",
                "job_id": job_id,
                "trigger": trigger,
                "status": summary["status"],
                "source_count": len(summary["sources"]),
            },
        )
        return summary

    def _recent_fetch_age_seconds(self, source_id: str, now: datetime) -> float | None:
        with storage.get_connection(self.db_path) as conn:
            return storage.recent_fetch_age_seconds(conn, source=source_id, now=now)

    def _active_refresh_job_locked(self) -> dict[str, Any] | None:
        if self._latest_refresh_job and self._latest_refresh_job["status"] in {"queued", "running"}:
            return self._latest_refresh_job
        return None

    def _finish_refresh_job(
        self,
        *,
        job_id: str | None,
        status: str,
        summary: dict[str, Any],
    ) -> None:
        if not job_id:
            return
        with self._job_state_lock:
            job = self._latest_refresh_job
            if not job or job["jobId"] != job_id:
                return
            job["status"] = status
            job["finishedAt"] = summary.get("finishedAt") or utc_now()
            job["summary"] = summary

    def _refresh_source(
        self,
        *,
        collector: Any,
        trigger: str,
        keywords: list[str],
        signal_rules: SignalRules,
    ) -> dict[str, Any]:
        source = collector.source
        started_at = utc_now()
        started = time.perf_counter()
        logger.info(
            "source refresh started",
            extra={"event": "source_refresh_started", "source": source.id, "trigger": trigger},
        )

        with storage.get_connection(self.db_path) as conn:
            run_id = storage.create_fetch_run(
                conn,
                source=source.id,
                trigger=trigger,
                started_at=started_at,
            )

        try:
            raw_items = collector.fetch()
            items = self._normalize_items(raw_items, source.id, source.section)
            apply_signal_scores(items, signal_rules)
            with storage.get_connection(self.db_path) as conn:
                saved = storage.save_hot_items(conn, items=items, keywords=keywords)
                storage.finish_fetch_run(
                    conn,
                    run_id=run_id,
                    source=source.id,
                    status="success",
                    duration_ms=(time.perf_counter() - started) * 1000,
                    items_count=saved,
                )
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "source refresh succeeded",
                extra={
                    "event": "source_refresh_success",
                    "source": source.id,
                    "trigger": trigger,
                    "items_count": saved,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return {"source": source.id, "status": "success", "itemsCount": saved}
        except CollectorError as exc:
            self._record_failure(
                run_id=run_id,
                source=source.id,
                started=started,
                error_type=exc.error_type,
                error_message=str(exc),
                http_status=exc.http_status,
                request_url=exc.request_url,
                response_snippet=exc.response_snippet,
            )
            logger.warning(
                "source refresh failed",
                extra={
                    "event": "source_refresh_failed",
                    "source": source.id,
                    "trigger": trigger,
                    "error_type": exc.error_type,
                    "http_status": exc.http_status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            return {"source": source.id, "status": "failed", "errorType": exc.error_type}
        except Exception as exc:  # noqa: BLE001 - collectors must never break the whole run.
            logger.exception(
                "unexpected collector failure",
                extra={
                    "event": "source_refresh_unexpected_failure",
                    "source": source.id,
                    "trigger": trigger,
                },
            )
            self._record_failure(
                run_id=run_id,
                source=source.id,
                started=started,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
            return {"source": source.id, "status": "failed", "errorType": exc.__class__.__name__}

    def _record_failure(
        self,
        *,
        run_id: int,
        source: str,
        started: float,
        error_type: str,
        error_message: str,
        http_status: int | None = None,
        request_url: str | None = None,
        response_snippet: str | None = None,
    ) -> None:
        with storage.get_connection(self.db_path) as conn:
            storage.record_fetch_error(
                conn,
                run_id=run_id,
                source=source,
                error_type=error_type,
                error_message=error_message,
                http_status=http_status,
                request_url=request_url,
                response_snippet=response_snippet,
            )
            storage.finish_fetch_run(
                conn,
                run_id=run_id,
                source=source,
                status="failed",
                duration_ms=(time.perf_counter() - started) * 1000,
                items_count=0,
                error_type=error_type,
                error_message=error_message,
                http_status=http_status,
            )

    @staticmethod
    def _normalize_items(items: list[HotItem], source_id: str, section: str) -> list[HotItem]:
        now = utc_now()
        normalized: list[HotItem] = []
        for item in items:
            item.source = source_id
            item.section = section
            item.fetchedAt = now
            normalized.append(item)
        return normalized


service = CollectionService()
