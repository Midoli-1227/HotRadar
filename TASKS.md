# HotRadar TASKS

Source of truth: `SPEC.md` (Draft v0.1, 2026-06-10).

Legend:

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done
- `[!]` Blocked or degraded but not project-blocking

## Phase 0: Project Scaffold

- [x] Create durable planning files: `TASKS.md` and `HANDOFF.md`.
- [x] Initialize backend FastAPI project structure.
- [x] Initialize frontend React + TypeScript project structure.
- [x] Add SQLite data directory placeholder.
- [x] Add `config/watch-keywords.json` with default keywords.
- [x] Add `.env.example`.
- [x] Add README with local startup and keyword-editing instructions.
- [x] Add `.gitignore` for runtime/generated files.

## Phase 1: Backend Core

- [x] Define unified `HotItem` model and API response shape.
- [x] Add centralized source configuration for all MVP sources:
  - [x] AI / Big Tech: OpenAI, Anthropic, Google, Microsoft, NVIDIA, Intel
  - [x] Tech / Startup: Hacker News, GitHub Trending, Product Hunt
  - [x] Market / Finance: 华尔街见闻、财联社
  - [x] Chinese Hot Topics: 知乎热榜、哔哩哔哩热门、微博热搜
- [x] Implement SQLite schema:
  - [x] `sources`
  - [x] `hot_items`
  - [x] `hot_item_snapshots`
  - [x] `fetch_runs`
  - [x] `fetch_errors`
  - [x] `source_status`
- [x] Implement storage layer with `source + normalizedUrl` deduplication.
- [x] Implement fallback dedupe by `source + title` when URL is unavailable.
- [x] Implement keyword config loader from `config/watch-keywords.json`.
- [x] Implement keyword matching across title, summary, source, and metadata.
- [x] Implement fetch run, source status, and error recording.
- [x] Ensure source failure never blocks other sources.
- [x] Ensure homepage API never exposes technical stack traces.

## Phase 2: Collectors

- [x] Add collector base interface and shared HTTP helpers with timeout protection.
- [~] Implement feed/API/scrape collectors where stable enough:
  - [x] OpenAI via RSS collector
  - [x] Anthropic via public news page HTML extraction
  - [x] Google via RSS collector
  - [x] Microsoft via RSS collector
  - [x] NVIDIA via RSS collector
  - [x] Intel via official Intel Investor Relations RSS collector
  - [x] Hacker News via official Firebase topstories order
  - [x] GitHub Trending via ranking article parser
  - [x] Product Hunt via public Atom feed order
  - [x] 华尔街见闻 via public 7x24 API
  - [x] 财联社 via public homepage HTML article extraction
  - [x] 知乎热榜 via public API
  - [x] 哔哩哔哩热门 via public API
  - [x] 微博热搜 via public hotSearch JSON
- [x] For unstable/API-key/login-limited sources, record Debug errors where retained; remove sources from MVP scope when explicitly cut.
- [x] Remove 雪球 from active MVP scope per user feedback because stable public collection requires session/cookie handling.
- [x] Remove 百度热搜 from active MVP scope per user feedback.
- [x] Add mock or fixture collectors for tests and offline development.

## Phase 3: Backend API and Scheduler

- [x] `GET /api/dashboard` returns theme sections, source panels, keyword match metadata, and refresh metadata.
- [x] `POST /api/refresh` triggers manual refresh with cooldown protection.
- [x] `GET /api/history` supports keyword, source, section, and time filters.
- [x] `GET /api/sources/status` returns source health status.
- [x] `GET /api/debug/sources` returns Debug table data.
- [x] Page-open refresh trigger is available from dashboard load.
- [x] Backend scheduled collection runs every 30 minutes.
- [x] Source-level short interval cache avoids repeated high-frequency requests.

## Phase 4: Dashboard Frontend

- [x] Homepage opens directly into dashboard.
- [x] Compact top toolbar with product name, global last refresh, manual refresh, History link, Debug link.
- [x] Theme order:
  - [x] AI / Big Tech
  - [x] Tech / Startup
  - [x] Market / Finance
  - [x] Chinese Hot Topics
- [x] Source panels show icon, name, last success time, fixed 5-item list, and homepage link where available.
- [x] Each source defaults to 5 items.
- [x] Each source panel stays capped at 5 visible items.
- [x] Dashboard adds a horizontal source jump bar below the top HotRadar toolbar.
- [x] Source jump bar includes all active source panels and smooth-scrolls to the selected panel.
- [x] Source jump bar stays horizontally scrollable on desktop and mobile.
- [x] Valid item URLs open in new tabs with `target="_blank"` and `rel="noopener noreferrer"`.
- [x] Invalid/missing URLs render safely as non-clickable titles.
- [x] Keyword matches are highlighted in source panels.
- [x] Keyword matches stay highlighted in original source panels.
- [x] Ranking source panels preserve source order; keyword matches do not reorder items.
- [x] AI / Big Tech official feed panels prioritize high/medium signal items and hide low signal items by default.
- [x] Source panels show signal badges and hidden low-signal counts where applicable.
- [x] Source panels display source icons.
- [x] Homepage does not expose technical error details.
- [x] Frontend local install/build/start verified with Homebrew npm.

## Phase 5: History and Debug Frontend

- [x] History page supports keyword search.
- [x] History page supports source filter.
- [x] History page supports section filter.
- [x] History page supports time range filter.
- [x] History results show title, source, section, first/last seen, seen count, latest rank/heat, URL.
- [x] Debug page `/debug/sources` shows source health table.
- [x] Debug table prioritizes failed sources.
- [x] Debug page includes latest error details for local troubleshooting.
- [x] Frontend visual/browser verification passed for Dashboard, History, and Debug.
- [x] Browser verification passed after removing My Watch, adding icons, and capping panels at 5 items.

## Phase 6: Verification

- [x] Backend unit tests.
- [x] Keyword matching tests.
- [x] URL deduplication tests.
- [x] Collector output structure tests.
- [x] API smoke tests for dashboard, history, refresh, and debug.
- [x] Frontend starts locally.
- [x] Dashboard API renders real/mock-ready data; demo SQLite data was seeded.
- [x] History API can search.
- [x] Debug API shows source status table.
- [x] README startup and keyword instructions added.
- [x] Signal scoring tests for official AI sources and ranking-source non-interference.
- [x] Add HotRadar-managed local domain gateway for HotRadar and Japanese Notebook.
- [x] Smoke-test local domain gateway with `Host` headers for HotRadar, Japanese Notebook, and HotRadar API proxy.
- [x] Install or confirm `/etc/hosts` entries for `hotradar.test` and `jpnote.test`.
- [x] Smoke-test local domain gateway through browser-compatible HTTP requests after hosts entries are installed.
- [x] Fix local-domain `Failed to fetch` by making frontend API requests relative and proxying `/api`.
- [x] Fix recurring local-domain `502` by creating project-local `.venv` and updating startup script to use it.
- [~] One-time Japanese Notebook localStorage migration helper opened from old origin; awaiting visual confirmation in browser.

## Acceptance Criteria Tracking

- [x] 首页按主题大板块展示。
- [x] 每个主题大板块下按来源小板块展示。
- [x] AI / Big Tech 包含 OpenAI、Anthropic、Google、Microsoft、NVIDIA、Intel。
- [x] Tech / Startup 包含 Hacker News、GitHub Trending、Product Hunt。
- [x] Market / Finance 包含 华尔街见闻、财联社。
- [x] Chinese Hot Topics 包含 知乎热榜、哔哩哔哩热门、微博热搜。
- [x] Ranking View 按来源站点/API/feed 的原始顺序展示，不因关键词命中重新排序。
- [x] AI / Big Tech 官方源支持 signalScore/signalLevel，首页默认隐藏 low signal 内容。
- [x] 每个来源默认显示 5 条。
- [x] 每个来源固定显示最多 5 条。
- [x] 每条有 URL 的内容标题都可以点击。
- [x] 点击后在新标签页打开原始来源页面。
- [x] 首页显示每个来源的最后成功更新时间。
- [x] 首页顶部支持按来源快速定位到对应板块。
- [x] 页面打开时触发刷新。
- [x] 手动刷新按钮可触发刷新。
- [x] 后端默认每 30 分钟自动采集。
- [x] 单个来源失败不影响其他来源。
- [x] 来源失败时首页显示上一次成功数据。
- [x] 首页不暴露具体技术错误。
- [x] Debug 页面显示来源状态表格。
- [x] SQLite 永久保存历史热点。
- [x] 历史页面支持关键词搜索。
- [x] 历史页面支持来源筛选。
- [x] 历史页面支持主题筛选。
- [x] 关键词高亮可用。
- [x] 首页不展示 My Watch / 我的关注聚合板块。
- [x] 关键词通过 `config/watch-keywords.json` 配置。
- [x] README 说明如何启动项目。
- [x] README 说明如何修改关键词。
- [x] 本地可运行后端和前端。
- [x] 本地域名入口已具备 HotRadar 侧脚本；系统 hosts 映射和 HTTP 验证已完成。
