from __future__ import annotations

import asyncio
import hmac
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from . import settings
from . import storage
from .logging_config import configure_logging
from .service import service
from .settings import ENABLE_SCHEDULER, SCHEDULED_REFRESH_MINUTES


async def scheduled_collection_loop() -> None:
    while True:
        await asyncio.sleep(SCHEDULED_REFRESH_MINUTES * 60)
        accepted, job = service.queue_refresh(trigger="scheduled", force=False)
        if accepted:
            await asyncio.to_thread(service.run_queued_refresh, job["jobId"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    service.bootstrap()
    scheduler_task: asyncio.Task | None = None
    if ENABLE_SCHEDULER:
        scheduler_task = asyncio.create_task(scheduled_collection_loop())
    try:
        yield
    finally:
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="HotRadar", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin_token(
    authorization: Annotated[str | None, Header()] = None,
    x_hotradar_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.REQUIRE_ADMIN_TOKEN:
        return
    if not settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token is required but HOTRADAR_ADMIN_TOKEN is not configured.",
        )

    provided = x_hotradar_admin_token
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()

    if not provided or not hmac.compare_digest(provided, settings.ADMIN_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid admin token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/")
def health() -> dict[str, str]:
    return {"name": "HotRadar", "status": "ok"}


@app.get("/api/dashboard")
def dashboard(background_tasks: BackgroundTasks) -> dict:
    accepted, job = service.queue_refresh(trigger="page_open", force=False)
    if accepted:
        background_tasks.add_task(service.run_queued_refresh, job["jobId"])
    payload = storage.get_dashboard_data(service.db_path)
    payload["refreshJob"] = service.get_latest_refresh_job()
    return payload


@app.post("/api/refresh", dependencies=[Depends(require_admin_token)])
def refresh(background_tasks: BackgroundTasks) -> dict:
    active = service.get_active_refresh_job()
    if active:
        return {
            "accepted": False,
            "status": "already_running",
            "jobId": active["jobId"],
        }

    allowed, retry_after_seconds = service.manual_refresh_allowed()
    if not allowed:
        return {
            "accepted": False,
            "status": "cooldown",
            "retryAfterSeconds": retry_after_seconds,
        }
    accepted, job = service.queue_refresh(trigger="manual", force=False)
    if accepted:
        background_tasks.add_task(service.run_queued_refresh, job["jobId"])
        return {"accepted": True, "status": "queued", "jobId": job["jobId"]}
    return {"accepted": False, "status": "already_running", "jobId": job["jobId"]}


@app.get("/api/refresh/status", dependencies=[Depends(require_admin_token)])
def refresh_status() -> dict:
    return {"latestJob": service.get_latest_refresh_job()}


@app.get("/api/history")
def history(
    q: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    section: Annotated[str | None, Query()] = None,
    start: Annotated[str | None, Query()] = None,
    end: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return storage.get_history(
        q=q,
        source=source,
        section=section,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
        db_path=service.db_path,
    )


@app.get("/api/sources/status", dependencies=[Depends(require_admin_token)])
def source_status() -> dict:
    return {"sources": storage.get_source_status_rows(service.db_path)}


@app.get("/api/debug/sources", dependencies=[Depends(require_admin_token)])
def debug_sources() -> dict:
    return {"sources": storage.get_source_status_rows(service.db_path)}
