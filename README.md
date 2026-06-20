# HotRadar

HotRadar 是一个本地优先的个人热点聚合工作台。第一版以 `SPEC.md` 为最高规格，使用 FastAPI、React + TypeScript 和 SQLite。

面向简历或面试说明时，应把它描述为本地优先的后端聚合 MVP：它已经具备持久化 snapshot、失败隔离 collector、Debug/状态 API、API 集成测试、Docker Compose、本地 migration 和 GitHub Actions 配置，但不应声称有生产用户、真实 AWS 部署或大规模流量。

## 当前能力

- 首页 dashboard 按主题和来源展示。
- 所有 MVP 来源都有配置、页面位置和 Debug 状态。
- SQLite 保存唯一热点和每次抓取 snapshot。
- 支持 `source + normalizedUrl` 去重，无稳定 URL 时退回 `source + title`。
- 支持 `config/watch-keywords.json` 关键词配置和命中高亮。
- 支持 `config/signal-rules.json` 对 AI / Big Tech 官方源做 high/medium/low 信号评分，首页默认隐藏低信号官方 PR 内容。
- 支持历史搜索、来源筛选、主题筛选、时间筛选。
- 支持 Debug 来源状态表格。
- 单个 collector 失败不会阻塞其他来源。
- 支持 API 级集成测试，使用临时 SQLite 和 fixture collector，避免依赖真实外网。
- 支持 Docker Compose 本地容器化运行。
- 支持 SQLite schema migration 记录。
- 支持可选 admin token 保护刷新和 Debug 类运维端点。
- 支持 refresh job 状态和重复刷新幂等控制。
- 支持 history offset 分页。
- 支持 JSON 结构化后端日志。

## Backend

安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

启动后端：

```bash
python3 -m uvicorn app.main:app --reload --app-dir backend
```

默认 API 地址：

- `GET http://127.0.0.1:8000/api/dashboard`
- `POST http://127.0.0.1:8000/api/refresh`
- `GET http://127.0.0.1:8000/api/refresh/status`
- `GET http://127.0.0.1:8000/api/history`
- `GET http://127.0.0.1:8000/api/debug/sources`

## Frontend

安装前端依赖并启动：

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：

```text
http://127.0.0.1:5173
```

前端默认通过相对路径 `/api` 请求后端。Vite dev server 会把 `/api` 代理到 `http://127.0.0.1:8000`。

如果后端地址不是 `http://127.0.0.1:8000`，可以设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

如果启用了 admin token 保护，并且只是本地自用，也可以让前端发送 token：

```bash
VITE_HOTRADAR_ADMIN_TOKEN=your-local-token npm run dev
```

不要在公开托管的前端构建中嵌入 admin token。

## Docker Compose

容器化本地运行：

```bash
docker compose up --build
```

默认访问：

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
```

Compose 包含两个服务：

- `backend`: FastAPI，读取 `/app/config`，SQLite 写入 `/app/data/hotspots.sqlite`。
- `frontend`: Nginx 静态托管 React build，并把 `/api/*` 代理到 backend。

SQLite 数据通过 `hotradar-data` Docker volume 持久化。需要离线演示时可以用 fixture collector：

```bash
HOTRADAR_COLLECTOR_MODE=fixture docker compose up --build
```

Docker、本地环境变量和未来部署计划的详细说明见 `DEPLOYMENT.md`。

## Local Domain Entrypoints

HotRadar can also serve two local projects through named local domains:

- HotRadar: `http://hotradar.test:8088`
- Japanese Notebook: `http://jpnote.test:8088`

Add the local domain mapping once:

```bash
sudo sh -c 'printf "\n127.0.0.1 hotradar.test jpnote.test\n" >> /etc/hosts'
```

Then start the local domain gateway:

```bash
bash scripts/start_local_domains.sh
```

The gateway serves the built HotRadar frontend, proxies HotRadar `/api/*` requests to the backend on `127.0.0.1:8000`, and serves the Japanese Notebook files from:

```text
/Users/lanyangyang/Documents/Japanese_notebook_codex
```

You can override the notebook path or domain names with environment variables:

```bash
HOTRADAR_JP_NOTEBOOK_ROOT=/path/to/Japanese_notebook_codex \
HOTRADAR_LOCAL_DOMAIN=hotradar.test \
JPNOTE_LOCAL_DOMAIN=jpnote.test \
bash scripts/start_local_domains.sh
```

## Demo / Offline Data

网络受限或真实来源暂时不可用时，可以写入 mock 数据验证页面：

```bash
python3 scripts/seed_demo_data.py
```

也可以使用 fixture collector 模式运行后端：

```bash
HOTRADAR_COLLECTOR_MODE=fixture python3 -m uvicorn app.main:app --reload --app-dir backend
```

`hybrid` 模式会尝试稳定的 RSS/API/HTML collector；暂不稳定、需要 API key、登录或反爬处理的数据源会在 Debug 页面记录失败状态。

## 运维端点保护

默认本地开发不要求 token。若准备把服务暴露到非本机环境，建议开启：

```bash
HOTRADAR_REQUIRE_ADMIN_TOKEN=1 \
HOTRADAR_ADMIN_TOKEN=change-me \
python3 -m uvicorn app.main:app --reload --app-dir backend
```

受保护端点包括：

- `POST /api/refresh`
- `GET /api/refresh/status`
- `GET /api/sources/status`
- `GET /api/debug/sources`

调用时使用任意一种 header：

```bash
curl -H "Authorization: Bearer change-me" http://127.0.0.1:8000/api/debug/sources
curl -H "X-HotRadar-Admin-Token: change-me" http://127.0.0.1:8000/api/debug/sources
```

## Refresh Job 状态

`POST /api/refresh` 返回 `accepted`、`status` 和 `jobId`。如果已有 refresh 在 queued/running 状态，新的请求会返回 `already_running`，不会重复启动 collector。

查看最新 refresh job：

```bash
curl http://127.0.0.1:8000/api/refresh/status
```

## History 分页

`GET /api/history` 支持：

- `q`
- `source`
- `section`
- `start`
- `end`
- `limit`
- `offset`

示例：

```bash
curl "http://127.0.0.1:8000/api/history?q=OpenAI&limit=50&offset=0"
```

返回值包含 `items` 和 `pagination`，其中 `pagination.hasMore` 表示是否还能继续加载。

## 修改关注关键词

关键词配置文件：

```text
config/watch-keywords.json
```

格式：

```json
{
  "keywords": ["AI", "OpenAI", "NVIDIA", "芯片"]
}
```

修改后，下次刷新会重新读取该文件。英文关键词大小写不敏感，中文关键词按原文包含匹配。JSON 格式错误时，后端会写清晰日志并回退到默认关键词。

## 修改官方源信号规则

信号规则配置文件：

```text
config/signal-rules.json
```

该机制只作用于 AI / Big Tech 官方源：

```json
{
  "enabledSources": ["openai", "anthropic", "google", "microsoft", "nvidia", "intel"],
  "hideLowSignalOnDashboard": true,
  "highSignal": [{ "term": "api", "weight": 4 }],
  "lowSignal": [{ "term": "customer story", "weight": -4 }]
}
```

命中 highSignal 会提高 `signalScore`，命中 lowSignal 会降低 `signalScore`。首页优先显示 high/medium，默认隐藏 low。历史数据仍会保存；Hacker News、GitHub Trending、Product Hunt 和中文热榜等 Ranking View 不受该机制影响。

## 测试

当前测试使用 Python 标准库 `unittest`，不依赖 `pytest`：

```bash
python3 -m unittest discover backend/tests
```

测试覆盖 collector、关键词匹配、信号评分、SQLite 存储、migration、history 分页，以及 FastAPI API 集成测试。API 测试使用临时 SQLite 和 fixture collector，不依赖真实外部网站。

前端构建检查需要先安装 `npm` 和前端依赖：

```bash
cd frontend
npm install
npm run build
```

GitHub Actions 配置位于 `.github/workflows/ci.yml`，会运行：

- Python backend tests。
- Frontend TypeScript/Vite build。

该 workflow 需要项目推送到 GitHub 后才会实际运行。

## Benchmark

本地 synthetic benchmark 见：

```text
BENCHMARK.md
```

运行：

```bash
python3 scripts/benchmark_api.py --sizes 1000 10000 --repeats 5
```

benchmark 默认使用临时 SQLite 和生成的 fixture 数据，不会修改生产数据，也不代表真实生产流量。

## Database Migrations

SQLite migration 文件位于：

```text
migrations/
```

启动后端时会自动应用未执行 migration，并记录到 `schema_migrations`。也可以手动执行：

```bash
python3 scripts/migrate_db.py
```

指定数据库路径：

```bash
python3 scripts/migrate_db.py --database data/hotspots.sqlite
```

## Logging

默认后端日志为 JSON：

```bash
HOTRADAR_LOG_FORMAT=json HOTRADAR_LOG_LEVEL=INFO python3 -m uvicorn app.main:app --app-dir backend
```

日志包含 refresh job start/finish、source success/failure、collector duration、cached-skip 和 unexpected exception。日志不会主动记录 admin token。

## Architecture

系统结构、数据流、失败处理、数据库表设计、API 列表和已知限制见：

```text
ARCHITECTURE.md
```

## 数据文件

默认 SQLite 文件：

```text
data/hotspots.sqlite
```

历史热点默认永久保存，不自动清理。
