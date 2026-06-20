# HotRadar Deployment

HotRadar is currently verified as a local-first application. This document covers local development, Docker Compose, environment variables, persistence, admin-token configuration, troubleshooting, and a future AWS deployment plan.

Do not describe this project as deployed on AWS unless that deployment has actually been completed and verified.

## Local Development

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --app-dir backend
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default local URLs:

- Backend health: `http://127.0.0.1:8000/`
- Dashboard API: `http://127.0.0.1:8000/api/dashboard`
- Frontend: `http://127.0.0.1:5173/`

For offline/demo mode, use fixture collectors:

```bash
HOTRADAR_COLLECTOR_MODE=fixture python3 -m uvicorn app.main:app --reload --app-dir backend
```

## Docker Compose Startup

Start Docker Desktop first, then run:

```bash
docker compose up --build
```

Default Compose URLs:

- Backend health: `http://127.0.0.1:8000/`
- Dashboard API: `http://127.0.0.1:8000/api/dashboard`
- Frontend through Nginx: `http://127.0.0.1:5173/`

For deterministic offline verification:

```bash
HOTRADAR_COLLECTOR_MODE=fixture docker compose up --build
```

Stop containers:

```bash
docker compose down
```

Stop containers and remove the SQLite volume:

```bash
docker compose down -v
```

## Latest Local Docker Verification

Verified locally on 2026-06-20 after starting Docker Desktop.

Commands run:

```bash
docker info --format '{{.ServerVersion}}'
docker compose config
docker compose up --build
curl -sS -o /tmp/hotradar_backend_health.txt -w '%{http_code}\n' http://127.0.0.1:8000/
curl -sS -o /tmp/hotradar_frontend.html -w '%{http_code}\n' http://127.0.0.1:5173/
curl -sS -o /tmp/hotradar_dashboard.json -w '%{http_code}\n' http://127.0.0.1:8000/api/dashboard
curl -sS -o /tmp/hotradar_frontend_dashboard.json -w '%{http_code}\n' http://127.0.0.1:5173/api/dashboard
docker compose down
```

Results:

- Docker daemon reachable: version `28.3.3`.
- `docker compose config`: valid.
- `docker compose up --build`: backend and frontend images built; containers started.
- `http://127.0.0.1:8000/`: HTTP `200`, response `{"name":"HotRadar","status":"ok"}`.
- `http://127.0.0.1:5173/`: HTTP `200`, React HTML returned.
- `http://127.0.0.1:8000/api/dashboard`: HTTP `200`, dashboard payload contained 4 sections.
- `http://127.0.0.1:5173/api/dashboard`: HTTP `200`, Nginx proxy returned dashboard payload with 4 sections.
- `docker compose ps`: backend was `healthy`; frontend was `Up`.
- `docker compose down`: containers and network removed; named SQLite volume retained.

## Environment Variables

Backend variables:

- `HOTRADAR_CONFIG_DIR`: directory containing JSON config files.
- `HOTRADAR_DATA_DIR`: data directory for SQLite.
- `HOTRADAR_DATABASE_PATH`: SQLite database path.
- `HOTRADAR_COLLECTOR_MODE`: `hybrid` or `fixture`.
- `HOTRADAR_HTTP_TIMEOUT_SECONDS`: collector HTTP timeout.
- `HOTRADAR_SCHEDULED_REFRESH_MINUTES`: scheduler interval.
- `HOTRADAR_MANUAL_REFRESH_COOLDOWN_SECONDS`: manual refresh cooldown.
- `HOTRADAR_SOURCE_MIN_REFRESH_SECONDS`: per-source cache freshness window.
- `HOTRADAR_ENABLE_SCHEDULER`: `1` to enable scheduled refresh, `0` to disable.
- `HOTRADAR_REQUIRE_ADMIN_TOKEN`: `1` to protect operational endpoints.
- `HOTRADAR_ADMIN_TOKEN`: token value for protected endpoints.
- `HOTRADAR_LOG_FORMAT`: `json` or plain text fallback.
- `HOTRADAR_LOG_LEVEL`: standard Python log level such as `INFO` or `DEBUG`.

Frontend variables:

- `VITE_API_BASE_URL`: optional backend URL override in local Vite development.
- `VITE_HOTRADAR_ADMIN_TOKEN`: optional local-only token forwarding for protected endpoints.

Do not embed `VITE_HOTRADAR_ADMIN_TOKEN` into a publicly served frontend build.

## SQLite Data Persistence

Local development defaults to:

```text
data/hotspots.sqlite
```

Docker Compose stores SQLite data in the named Docker volume:

```text
hotradar-data
```

The backend applies SQL migrations from `migrations/` on startup and records versions in `schema_migrations`. Migrations can also be applied manually:

```bash
python3 scripts/migrate_db.py
```

## Admin Token Configuration

By default, local development does not require an admin token. Enable token protection before exposing the backend beyond localhost:

```bash
HOTRADAR_REQUIRE_ADMIN_TOKEN=1 \
HOTRADAR_ADMIN_TOKEN=change-me \
python3 -m uvicorn app.main:app --app-dir backend
```

Protected endpoints:

- `POST /api/refresh`
- `GET /api/refresh/status`
- `GET /api/sources/status`
- `GET /api/debug/sources`

Example requests:

```bash
curl -H "Authorization: Bearer change-me" http://127.0.0.1:8000/api/debug/sources
curl -H "X-HotRadar-Admin-Token: change-me" http://127.0.0.1:8000/api/debug/sources
```

## Troubleshooting

Docker daemon is unavailable:

```text
Cannot connect to the Docker daemon
```

Start Docker Desktop and retry:

```bash
open -a Docker
docker info
```

Port `8000` or `5173` is already in use:

```bash
lsof -i :8000
lsof -i :5173
```

Stop the conflicting process or change the Compose port mapping.

Frontend loads but API calls fail:

- Confirm backend is healthy: `curl http://127.0.0.1:8000/`.
- Confirm the Nginx frontend proxy is running: `curl http://127.0.0.1:5173/api/dashboard`.
- In Vite development, confirm `frontend/vite.config.ts` proxies `/api` to the backend.

Collectors fail in Docker:

- Use fixture mode to separate Docker/runtime issues from live website issues:

```bash
HOTRADAR_COLLECTOR_MODE=fixture docker compose up --build
```

- Check backend logs for structured `source_refresh_failed` entries.

SQLite state looks stale:

- Check the mounted volume with `docker volume ls`.
- Reset local Compose data only when intentional:

```bash
docker compose down -v
```

Protected endpoints return `401`:

- Set `HOTRADAR_ADMIN_TOKEN`.
- Send `Authorization: Bearer <token>` or `X-HotRadar-Admin-Token: <token>`.

Protected endpoints return `503`:

- `HOTRADAR_REQUIRE_ADMIN_TOKEN=1` is set but `HOTRADAR_ADMIN_TOKEN` is empty.

## Future AWS Deployment Plan

Future AWS deployment option: EC2 + Docker Compose or ECS/Fargate.

EC2 + Docker Compose would be the simplest path:

1. Build and run the same Compose services on an EC2 instance.
2. Store configuration in environment variables or AWS Systems Manager Parameter Store.
3. Persist SQLite on an attached EBS volume, or migrate to a managed database if multi-user usage appears.
4. Put the frontend/backend behind a reverse proxy and restrict operational endpoints with admin-token protection.
5. Stream logs to CloudWatch.
6. Add backups for the data volume.

ECS/Fargate would be a stronger container-native option:

1. Build backend and frontend images.
2. Push images to ECR.
3. Run services on ECS/Fargate.
4. Replace local SQLite with persistent storage or a managed database before claiming production readiness.
5. Configure secrets and logs through AWS-managed services.

This project has not been deployed to AWS yet.
