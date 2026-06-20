# HotRadar SPEC

Status: Draft v0.1
Date: 2026-06-10

## 1. Product Goal

HotRadar 是一个面向个人使用的综合热点聚合网站。

它收集多个网站、社区、媒体和公司官方源的热点、趋势或最新动态，并按主题板块分类展示，帮助用户更快发现可能影响美股、AI、半导体、科技行业和中文互联网舆论的重要信息。

第一版目标：

- 聚合多个来源的热点、趋势或最新动态。
- 首页按主题大板块展示。
- 每个主题大板块下按具体来源展示小板块。
- 每条内容保留原始链接，点击后在新标签页打开原站页面。
- 支持关键词高亮；首页不再单独展示“我的关注”聚合板块。
- 保存历史热点，默认永久保存。
- 提供简单历史页面。
- 提供简单 Debug 页面，用于排查数据源采集状态。
- 本地运行优先，同时保留未来部署到服务器的能力。

## 2. Product Stage

当前阶段：Personal MVP。

第一版主要面向用户本人使用，不以公开服务、多人使用或商业化访问为目标。

Implications:

- 暂不需要用户注册。
- 暂不需要用户登录。
- 暂不需要复杂权限系统。
- 暂不需要多人偏好同步。
- 刷新频率以个人使用为准，避免高频请求。
- 架构要保留未来公开部署的可能性。

## 3. Non-goals

第一版暂不做：

- 用户注册/登录系统。
- 多用户权限系统。
- 移动 App。
- 复杂后台管理系统。
- 复杂趋势图。
- 自动日报/周报。
- AI 总结。
- 股票影响评分。
- 热点聚类。
- 跨平台话题合并。
- 全文内容抓取或全文归档。
- 未授权的大规模爬取。

## 4. Reference Product

Reference:

- ourongxing/newsnow
- https://github.com/ourongxing/newsnow

Borrow:

- 多来源热点聚合。
- 每个来源独立 collector。
- 统一 HotItem / NewsItem 数据结构。
- 每条热点必须包含原站 URL。
- 缓存与刷新间隔。
- 来源配置集中管理。

Do not blindly copy:

- 不直接照搬 UI。
- 不一开始做 GitHub OAuth。
- 不一开始做 MCP server。
- 不为了支持大量来源而牺牲第一版稳定性。

## 5. Key Questions

### 5.1 谁会使用？

第一版主要由用户本人使用。

### 5.2 输入是什么？

来自多个网站、社区、媒体和公司官方源的热点、趋势、热门内容或最新动态。

### 5.3 输出是什么？

一个本地运行的聚合网站。

首页按照主题大板块展示热点信息，每条内容可以跳转到原始来源页面。

### 5.4 哪些情况不允许？

- 不应该因为单个来源失败导致整个网站不可用。
- 不应该无限频率请求目标网站。
- 不应该抓取登录后私密内容。
- 不应该丢失原始来源链接。
- 不应该在首页暴露技术错误堆栈。
- 不应该自动覆盖用户配置。

### 5.5 出错怎么处理？

- 某个来源刷新失败时，优先显示上一次成功数据。
- 首页只显示最后成功更新时间，不显示具体技术错误。
- 错误详情写入数据库和日志。
- Debug 页面用于查看失败原因。

## 6. Data Sources

第一版计划支持以下全部来源。

### 6.1 AI / Big Tech

Sources:

- OpenAI
- Anthropic
- Google
- Microsoft
- NVIDIA
- Intel

Purpose:

展示 AI、大模型、半导体、大型科技公司的重要更新。

Display type:

- Feed View

### 6.2 Tech / Startup

Sources:

- Hacker News
- GitHub Trending
- Product Hunt

Purpose:

展示技术社区、开源项目、创业产品和开发者趋势。

Display type:

- Ranking View or Feed View, depending on source.

### 6.3 Market / Finance

Sources:

- 华尔街见闻
- 财联社

Purpose:

展示可能影响市场情绪、美股投资判断、宏观经济和公司动态的热点信息。

Display type:

- Ranking View or Feed View, depending on source.

### 6.4 Chinese Hot Topics

Sources:

- 知乎热榜
- 哔哩哔哩热门
- 微博热搜

Purpose:

展示中文互联网正在讨论的公共话题、社会热点和舆论趋势。

Display type:

- Ranking View

## 7. Source Completion Rule

第一版目标是接入全部 MVP sources。

如果某个来源因为接口不可用、反爬、登录限制、API key 缺失或合规问题暂时无法稳定获取：

- 不能因为该来源阻塞整个项目。
- 该来源应保留 collector 接口和页面位置。
- 首页不显示具体技术错误。
- Debug 页面显示该来源的失败状态和原因。
- 该来源后续可以继续修复。

Scope update:

- 雪球因公开访问长期受 WAF、登录态或 Cookie 限制影响，已从第一版 active sources 中移除；后续如有稳定合规来源再重新评估。

## 8. Information Architecture

首页默认按主题分区展示。

结构：

```text
Theme Section
  Source Panel
    Hot Items / Feed Items
```

首页顺序：

1. AI / Big Tech
2. Tech / Startup
3. Market / Finance
4. Chinese Hot Topics

每个 Source Panel 展示：

- 来源名称。
- 最近成功更新时间。
- 热点/动态列表。
- 固定显示前 5 条内容。
- 如果可用，提供跳转来源站点的入口。

## 9. Homepage Layout

首页直接进入 dashboard，不做 landing page。

顶部工具栏包含：

- 产品名称。
- 全局最后刷新时间。
- 手动刷新按钮。
- 历史页面入口。
- Debug 页面入口。

主体区域：

- 按主题大板块展示。
- 每个主题大板块中包含多个来源小板块。

## 10. List Size

每个 Source Panel 只显示前 5 条内容。

第一版不再提供展开按钮，避免单个来源面板过长影响扫描效率。

Rules:

- 固定显示 5 条。
- 如果该来源总数不足 5 条，则显示全部。
- 如果该来源超过 5 条，首页只显示前 5 条。
- 展示数量只影响前端展示，不影响数据采集数量。

## 11. Link Behavior

每条热点、趋势或官方动态都必须保留原始来源链接。

用户点击标题时，应在新标签页打开原始来源页面。

Rules:

- 所有可点击标题使用原始 `url` 字段。
- 链接必须使用完整 URL。
- 点击链接时使用新标签页打开。
- 前端链接应使用 `target="_blank"`。
- 前端链接应使用 `rel="noopener noreferrer"`。
- 如果某条内容没有有效 URL，则标题不显示为可点击状态。
- 无效链接不能导致页面崩溃。

## 12. Item Display

每条热点或动态至少展示：

- 标题。
- 来源。
- 原始链接。
- 发布时间或抓取时间。
- 排名，如果来源提供。
- 热度、评论数、分数、播放量等指标，如果来源提供。
- 简短摘要，如果来源提供。
- 命中的关注关键词，如果有。

## 13. Display Types

### 13.1 Ranking View

用于热榜类来源。

Ordering rules:

- Ranking View 必须按照来源站点或来源 API 返回的原始排名顺序展示。
- `rank` 应来自来源站点、来源 API 或来源 feed 的原始位置。
- 关键词匹配只用于高亮和历史检索，不允许改变来源面板中的条目顺序。
- 不允许因为命中关键词、抓取时间、缓存时间或本地评分对 Ranking View 重新排序。

每条显示：

- rank
- title
- url
- heat / score / comments，如果来源提供
- source
- fetchedAt

### 13.2 Feed View

用于官方新闻、博客、公告类来源。

每条显示：

- title
- url
- summary，如果来源提供
- publishedAt，如果来源提供
- source
- fetchedAt

## 14. Refresh Strategy

系统默认自动刷新频率为 30 分钟。

首页每次打开时，应主动触发一次数据刷新，尽量展示最新数据。

页面提供手动刷新按钮，用户可以主动请求重新获取所有来源数据。

Rules:

- 页面首次打开时触发刷新。
- 页面保持打开时，每 30 分钟自动刷新一次。
- 用户可以点击手动刷新按钮立即刷新。
- 刷新时不应阻塞页面展示，可以先显示缓存数据，再更新为新数据。
- 单个来源刷新失败不影响其他来源。
- 刷新失败时保留该来源上一次成功获取的数据。
- 每个来源显示最近成功更新时间。

## 15. Collection Strategy

系统同时支持三种采集触发方式：

1. Page Open Refresh
   - 用户打开首页时触发刷新，尽量展示最新数据。

2. Manual Refresh
   - 用户点击刷新按钮时立即触发刷新。

3. Background Scheduled Collection
   - 后端运行时自动定时采集，用于持续沉淀历史热点。

Default frequency:

- 后台自动采集默认每 30 分钟执行一次。

Collection rules:

- 页面打开时可以触发一次刷新。
- 手动刷新按钮可以触发一次刷新。
- 后台默认每 30 分钟自动采集一次。
- 如果某来源刚刚刷新过，应优先使用缓存，避免重复请求。
- 单个来源失败不影响其他来源。
- 每次成功采集都应写入历史数据库。
- 每次采集任务应记录 fetch_runs。
- 采集错误应记录 fetch_errors。

## 16. Rate Limit Protection

为避免频繁请求目标网站，系统应对刷新请求做基础保护。

Rules:

- 手动刷新按钮应有短暂冷却时间。
- 同一来源短时间内不应重复高频请求。
- 如果某来源刚刚刷新成功，可以直接使用缓存。
- 后续可以为不同来源配置不同刷新间隔。

## 17. Source Failure Behavior

首页不直接暴露具体技术错误。

如果某个来源刷新失败，但该来源之前有成功数据：

- 首页继续显示上一次成功获取的数据。
- 首页显示该来源的最后成功更新时间。
- 首页不显示详细错误信息。
- 首页不显示技术报错堆栈。
- 该次失败记录写入后台日志和数据库。

如果某个来源刷新失败，且该来源从未成功获取过数据：

- 首页显示该来源板块。
- 该板块显示空状态。
- 首页仍不显示具体技术错误。
- 失败详情写入后台日志和数据库。

## 18. History Storage

第一版需要保存历史热点。

历史数据使用 SQLite 存储。

Database file:

- `data/hotspots.sqlite`

Retention:

- 历史热点默认永久保存。
- 系统不自动删除历史热点数据。

Rules:

- 每次成功抓取的数据都应写入历史数据库。
- 同一个热点不应无限重复创建主记录。
- 同一热点的不同抓取时间、排名、热度变化应作为 snapshot 保存。
- 历史数据默认不清理。
- 后续可以增加手动清理、导出、归档功能，但第一版不自动删除。

## 19. Deduplication

热点主记录按 `source + normalizedUrl` 去重。

如果同一个来源再次抓取到相同 URL：

- 不新建 hot_items。
- 更新 lastSeenAt。
- 新增一条 hot_item_snapshots。

如果来源没有稳定 URL：

- 使用 `source + title` 作为备用去重键。

## 20. Database Tables

第一版建议包含以下表：

### 20.1 sources

保存来源配置。

Fields:

- id
- name
- section
- displayType
- homepageUrl
- enabled
- refreshIntervalMinutes

### 20.2 hot_items

保存唯一热点条目。

Fields:

- id
- source
- section
- title
- url
- normalizedUrl
- firstSeenAt
- lastSeenAt

### 20.3 hot_item_snapshots

保存每次抓取时的状态。

Fields:

- id
- itemId
- source
- rank
- heat
- summary
- fetchedAt
- matchedKeywords

### 20.4 fetch_runs

记录每次采集任务。

Fields:

- id
- source
- status: success / failed
- startedAt
- finishedAt
- durationMs
- itemsCount
- trigger: page_open / manual / scheduled

### 20.5 fetch_errors

记录采集失败原因。

Fields:

- id
- runId
- source
- errorType
- errorMessage
- httpStatus
- requestUrl
- responseSnippet
- createdAt

### 20.6 source_status

记录每个来源当前状态。

Fields:

- source
- lastSuccessAt
- lastFetchAt
- lastFailureAt
- consecutiveFailures
- latestErrorType
- latestHttpStatus
- latestErrorMessage
- averageDurationMs
- latestItemsCount

## 21. History Page

第一版需要提供一个简单历史页面。

复杂趋势图、热度曲线、日报周报等高级分析功能放到后续版本。

History page MVP:

- 按关键词搜索历史热点。
- 按来源筛选。
- 按主题大板块筛选。
- 按时间范围筛选。
- 查看标题、来源、首次出现时间、最近出现时间、出现次数。
- 点击标题跳转原始来源页面。

History item display:

- title
- source
- section
- firstSeenAt
- lastSeenAt
- seenCount
- latestRank，如果有
- latestHeat，如果有
- url

## 22. Keyword Watch

第一版需要支持关键词关注功能。

用户可以配置一组关注关键词。系统在展示热点时，如果标题、摘要或来源信息命中关键词，应进行高亮显示。

首页不再提供 My Watch / 我的关注聚合板块，避免重复展示。

Rules:

- 关键词匹配范围包括 title。
- 关键词匹配范围包括 summary。
- 关键词匹配范围包括 source。
- 关键词匹配范围包括 extra metadata，如果来源提供。
- 命中关键词的内容在原来源板块中应高亮显示。
- 命中关键词的内容保留在原来源板块中展示。
- 关键词匹配不得改变来源面板内的原始排名顺序。
- 点击标题仍然在新标签页打开原始来源页面。
- 同一条内容命中多个关键词时，展示命中的关键词列表。

## 23. Initial Watch Keywords

第一版默认关注关键词：

- AI
- OpenAI
- Anthropic
- Google
- Cloud
- Gemini
- ChatGPT
- NVIDIA
- 半导体
- 芯片
- 美股
- 美联储
- 纳斯达克
- 标普500

## 24. Keyword Config

第一版通过配置文件维护关注关键词，不提供网页管理界面。

File:

- `config/watch-keywords.json`

Initial content:

```json
{
  "keywords": [
    "AI",
    "OpenAI",
    "Anthropic",
    "Google",
    "Cloud",
    "Gemini",
    "ChatGPT",
    "NVIDIA",
    "半导体",
    "芯片",
    "美股",
    "美联储",
    "纳斯达克",
    "标普500"
  ]
}
```

Rules:

- 用户通过编辑 `config/watch-keywords.json` 添加、删除或修改关键词。
- 应用启动或刷新时读取该配置。
- 第一版不提供关键词管理页面。
- README 中必须说明如何修改关键词。
- 如果 JSON 格式错误，后端应给出清晰错误日志。

Keyword matching rules:

- 英文关键词大小写不敏感。
- 中文关键词按原文匹配。
- 标题和摘要中包含关键词即视为命中。
- 同一条内容命中多个关键词时，只在原来源条目上展示一次。
- 展示命中的关键词列表。

## 25. Debug Page

## 25. Official Source Signal Scoring

第一版需要对 AI / Big Tech 官方 Feed View 来源增加轻量信号评分，用于降低官方 PR 套话在首页的视觉权重。

Scope:

- 只用于 OpenAI、Anthropic、Google、Microsoft、NVIDIA、Intel。
- 不用于 Hacker News、GitHub Trending、Product Hunt、知乎热榜、微博热搜等 Ranking View。
- 不改变 Ranking View 的源站原始顺序。

Config file:

- `config/signal-rules.json`

Rules:

- 命中 highSignal term 时增加 `signalScore`。
- 命中 lowSignal term 时降低 `signalScore`。
- 分数映射为 `signalLevel`: `high`、`medium`、`low`。
- 评分结果用轻量方案写入 item `extra`，包括 `signalScore`、`signalLevel`、`signalReasons`。
- 首页 AI / Big Tech 官方源优先展示 high，其次 medium。
- low signal 默认不在首页展示，但仍保存到 SQLite 历史和 Debug/History 可排查数据中。
- 关键词高亮和 signal scoring 是两套机制；关键词不改变排序，signal scoring 只改变官方 Feed View 的展示优先级。

## 26. Debug Page

第一版提供简单 Debug 页面。

Path:

- `/debug/sources`

Purpose:

- 查看各数据源的采集健康状态。
- 排查某个来源为什么没有更新。
- 避免把技术错误直接暴露在首页。

Display:

Debug 页面以表格形式展示每个数据源状态。

Fields:

- Source Name
- Section
- Last Fetch Time
- Last Success Time
- Last Failure Time
- Current Status
- Items Fetched
- Consecutive Failures
- Latest Error Type
- Latest HTTP Status
- Latest Error Message
- Average Duration
- Last Run Trigger

Rules:

- Debug 页面不需要复杂 UI。
- 第一版只需要一个系统状态表格。
- 表格可以按失败状态优先排序。
- 首页不显示具体技术错误，Debug 页面显示排查信息。

Security:

- 第一版本地运行时可直接访问 `/debug/sources`。
- 未来部署到公网前，必须为 Debug 页面增加访问保护。

## 26. Authentication / Authorization

第一版本地个人使用，不做用户登录系统。

Rules:

- 首页不需要登录。
- 历史页面不需要登录。
- Debug 页面第一版本地运行时不需要登录。
- 不实现多用户系统。
- 不实现用户注册。
- 不实现用户角色权限。

Future security requirement:

如果未来部署到公网，必须补充访问保护：

- Debug 页面必须加访问控制。
- 手动刷新接口必须防止被公开滥用。
- 配置页面如果存在，必须加访问控制。
- 后端 API 需要考虑基础鉴权或访问限制。

## 27. Tech Stack

第一版采用：

- Backend: Python FastAPI
- Frontend: React + TypeScript
- Database: SQLite
- Data Collection: Python collectors
- Scheduler: backend scheduled jobs

Rationale:

该项目后续重点包括历史热点沉淀、关键词追踪、趋势分析和 AI 辅助总结。Python 后端更适合数据采集、清洗、分析和后续机器学习/LLM 工作；React 前端更适合构建可交互的信息 dashboard。

## 28. Local-first Deployment Strategy

第一版以本地运行为主，同时保留未来部署到服务器的能力。

当前阶段不要求公网部署，不要求域名，不要求云数据库。

后续购买服务器后，再部署为长期运行的个人网站或半公开网站。

Local-first requirements:

- 后端 FastAPI 可在本地运行。
- 前端 React 可在本地运行。
- SQLite 数据库保存在本地。
- 提供清晰的 README 启动说明。
- 提供环境变量示例文件。
- 不依赖必须付费的云服务才能运行。

Future deployment readiness:

- 后端和前端分离。
- 数据库访问通过统一模块封装。
- 配置通过环境变量管理。
- 数据源 collector 独立封装。
- 日志和错误记录可迁移到服务器环境。
- SQLite 后续可迁移到 PostgreSQL。
- 定时任务后续可迁移到服务器 cron / systemd / Celery / APScheduler。

## 29. Visual Style

前端采用现代 dashboard 风格，同时保留较高信息密度。

设计目标不是营销页，也不是博客页，而是一个适合频繁查看的信息工作台。

Style direction:

- 现代、清爽、克制。
- 信息密度高。
- 适合快速扫描。
- 类似金融终端的信息组织效率。
- 避免过度装饰。
- 避免大面积营销式 hero。
- 避免过大的卡片和留白。

UI layout rules:

- 首页直接进入 dashboard，不做 landing page。
- 页面顶部提供紧凑工具栏。
- 首页主体按主题分区。
- 每个主题区内按来源展示小面板。
- 每个来源小面板固定显示最多 5 条。
- 小面板应该紧凑，但不能拥挤到难以阅读。
- 标题优先，摘要和 metadata 次之。
- 重要关键词高亮，但不要刺眼。

Design constraints:

- 不做大幅 hero 区。
- 不使用营销页式大标题。
- 不使用过度圆角和大面积渐变。
- 不做低信息密度的装饰卡片。
- 内容区优先使用列表、紧凑面板、标签、时间戳和来源标识。
- 桌面端优先支持高效浏览。
- 移动端必须可读，但第一版以桌面使用为主。

## 30. API Requirements

Backend should expose API endpoints for:

- 获取首页聚合数据。
- 触发手动刷新。
- 获取历史搜索结果。
- 获取来源状态。
- 获取 Debug 页面数据。

Suggested endpoints:

- `GET /api/dashboard`
- `POST /api/refresh`
- `GET /api/history`
- `GET /api/sources/status`
- `GET /api/debug/sources`

## 31. Collector Requirements

每个来源应有独立 collector。

Collector 输出统一 HotItem 格式。

Suggested normalized item:

```ts
type HotItem = {
  id: string
  source: string
  section: string
  rank?: number
  title: string
  url: string
  mobileUrl?: string
  heat?: string
  summary?: string
  author?: string
  publishedAt?: string
  fetchedAt: string
  matchedKeywords?: string[]
}
```

Collector rules:

- Collector 不应直接操作 UI。
- Collector 负责抓取和解析。
- Normalizer 负责输出统一结构。
- Storage layer 负责写入数据库。
- 单个 collector 失败不能影响其他 collector。

## 32. Testing / Verification

第一版至少需要：

- 后端基础单元测试。
- 关键词匹配测试。
- URL 去重测试。
- Collector 输出结构测试。
- API smoke test。
- 前端页面可启动。
- 首页展示真实或 mock 数据。
- 历史页面能搜索。
- Debug 页面能显示来源状态表格。

如果某些真实来源因为网络、反爬或 API key 无法稳定测试，应提供 mock 数据或 fixture 测试。

## 33. Acceptance Criteria

- [ ] 首页按主题大板块展示。
- [ ] 每个主题大板块下按来源小板块展示。
- [ ] AI / Big Tech 包含 OpenAI、Anthropic、Google、Microsoft、NVIDIA、Intel。
- [ ] Tech / Startup 包含 Hacker News、GitHub Trending、Product Hunt。
- [ ] Market / Finance 包含 华尔街见闻、财联社。
- [ ] Chinese Hot Topics 包含 知乎热榜、哔哩哔哩热门、微博热搜。
- [ ] Ranking View 按来源站点/API/feed 的原始顺序展示，不因关键词命中重新排序。
- [ ] AI / Big Tech 官方源支持 signalScore/signalLevel，首页默认隐藏 low signal 内容。
- [ ] 每个来源默认显示 5 条。
- [ ] 每个来源固定显示最多 5 条。
- [ ] 每条有 URL 的内容标题都可以点击。
- [ ] 点击后在新标签页打开原始来源页面。
- [ ] 首页显示每个来源的最后成功更新时间。
- [ ] 页面打开时触发刷新。
- [ ] 手动刷新按钮可触发刷新。
- [ ] 后端默认每 30 分钟自动采集。
- [ ] 单个来源失败不影响其他来源。
- [ ] 来源失败时首页显示上一次成功数据。
- [ ] 首页不暴露具体技术错误。
- [ ] Debug 页面显示来源状态表格。
- [ ] SQLite 永久保存历史热点。
- [ ] 历史页面支持关键词搜索。
- [ ] 历史页面支持来源筛选。
- [ ] 历史页面支持主题筛选。
- [ ] 关键词高亮可用。
- [ ] 首页不展示 My Watch / 我的关注聚合板块。
- [ ] 关键词通过 `config/watch-keywords.json` 配置。
- [ ] README 说明如何启动项目。
- [ ] README 说明如何修改关键词。
- [ ] 本地可运行后端和前端。

## 34. Codex Execution Protocol

Codex 后续开发必须以本 SPEC 为最高产品规格。

### 34.1 Start-of-session Checklist

每次开始工作时，Codex 应先执行：

1. 阅读 `SPEC.md`。
2. 检查项目结构。
3. 检查 `git status`。
4. 如果存在 `TASKS.md`，读取当前任务进度。
5. 如果存在 `HANDOFF.md`，读取最新交接状态。
6. 不覆盖用户已有改动。

### 34.2 Planning Files

Codex 应基于本 SPEC 创建和维护：

- `TASKS.md`
- `HANDOFF.md`

`TASKS.md` 用于拆分实现任务。

`HANDOFF.md` 用于记录当前进度、已修改文件、运行过的命令、测试结果、阻塞问题和下一步。

### 34.3 Work Loop

Codex 应按以下循环工作：

1. 从 `TASKS.md` 选择下一个未完成任务。
2. 阅读相关代码。
3. 实现最小可验证改动。
4. 运行相关测试或启动检查。
5. 检查 diff。
6. 更新 `TASKS.md`。
7. 更新 `HANDOFF.md`。
8. 继续下一个任务。

### 34.4 Context / Overnight Rule

长时间工作或通宵工作时：

- 每完成一个阶段，更新 `HANDOFF.md`。
- 每次重要决策后，更新 `HANDOFF.md`。
- 每次测试或验证后，更新 `HANDOFF.md`。
- 如果上下文变长，先更新 `HANDOFF.md` 再继续。
- 如果需要新开对话，先读取 `SPEC.md`、`TASKS.md`、`HANDOFF.md` 再继续。

### 34.5 Do-not-do Rules

Codex 不应：

- 在没有必要时大改架构。
- 为了好看牺牲信息密度。
- 删除用户配置。
- 覆盖用户未提交改动。
- 因单个来源失败阻塞整个项目。
- 在首页显示详细技术错误。
- 把 Debug 页面当作公开页面设计。

## 35. Suggested Implementation Phases

### Phase 0: Project Scaffold

- 初始化后端 FastAPI 项目。
- 初始化前端 React + TypeScript 项目。
- 添加 SQLite 数据目录。
- 添加基础 README。
- 添加 `config/watch-keywords.json`。

### Phase 1: Backend Core

- 数据库 schema。
- 数据模型。
- 来源配置。
- 关键词匹配。
- 采集运行记录。
- 错误记录。

### Phase 2: Collectors

- 实现优先级较高、稳定性较好的 collectors。
- 所有 collectors 输出统一 HotItem。
- 对不稳定来源提供明确错误记录。

### Phase 3: Dashboard Frontend

- 首页主题分区。
- 来源小面板。
- 固定显示最多 5 条。
- 新标签页打开原始链接。
- 关键词高亮。
- 关键词高亮保留在来源面板中。
- 手动刷新按钮。

### Phase 4: History / Debug

- 历史页面。
- 历史搜索和筛选。
- Debug 页面 `/debug/sources`。
- 来源状态表格。

### Phase 5: Scheduler / Verification

- 后台 30 分钟定时采集。
- 页面打开刷新。
- 手动刷新冷却。
- 测试和 README。
- 本地启动验证。

## 36. Resume Prompt

新开 Codex 对话时，可以使用以下提示：

```text
请读取项目根目录的 SPEC.md、TASKS.md 和 HANDOFF.md。

以 SPEC.md 作为最高产品规格，继续完成 HotRadar 项目。

请先检查 git status 和项目结构，确认当前进度后，从 TASKS.md 选择下一个未完成任务继续实现。

工作过程中：
- 不要覆盖用户已有改动。
- 每完成一个阶段更新 HANDOFF.md。
- 每次重要测试或验证后更新 HANDOFF.md。
- 如果某个数据源暂时无法稳定实现，不要阻塞整个项目，应记录到 Debug/日志体系并继续推进其他任务。
```
