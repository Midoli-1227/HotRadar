import { FormEvent, useEffect, useMemo, useState } from 'react';
import { fetchDashboard, fetchDebugSources, fetchHistory, triggerRefresh } from './api';
import type { DashboardResponse, DebugSource, HistoryItem, HotItem, SignalLevel, SourcePanel } from './types';

type Page = 'dashboard' | 'history' | 'debug';

const PAGE_PATH: Record<Page, string> = {
  dashboard: '/',
  history: '/history',
  debug: '/debug/sources',
};

function pageFromPath(): Page {
  if (window.location.pathname.startsWith('/history')) return 'history';
  if (window.location.pathname.startsWith('/debug')) return 'debug';
  return 'dashboard';
}

function formatTime(value?: string | null): string {
  if (!value) return 'Never';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function isValidUrl(value?: string | null): boolean {
  if (!value) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function HighlightedText({ text, keywords }: { text: string; keywords: string[] }) {
  const active = keywords.filter(Boolean).sort((a, b) => b.length - a.length);
  if (!active.length) return <>{text}</>;
  const pattern = new RegExp(`(${active.map(escapeRegExp).join('|')})`, 'gi');
  const parts = text.split(pattern);

  return (
    <>
      {parts.map((part, index) => {
        const matched = active.some((keyword) => keyword.toLowerCase() === part.toLowerCase());
        return matched ? <mark key={`${part}-${index}`}>{part}</mark> : part;
      })}
    </>
  );
}

function StatusPill({ status }: { status: SourcePanel['currentStatus'] | DebugSource['currentStatus'] }) {
  return <span className={`status status-${status}`}>{status.replace('_', ' ')}</span>;
}

function signalLevelForItem(item: HotItem): SignalLevel | null {
  const level = item.extra?.signalLevel;
  return level === 'high' || level === 'medium' || level === 'low' ? level : null;
}

function signalScoreForItem(item: HotItem): number | null {
  const score = item.extra?.signalScore;
  return typeof score === 'number' ? score : null;
}

function SignalBadge({ item }: { item: HotItem }) {
  const level = signalLevelForItem(item);
  if (!level) return null;
  const score = signalScoreForItem(item);
  return (
    <span className={`signal-badge signal-${level}`}>
      {level} signal{score === null ? '' : ` ${score > 0 ? '+' : ''}${score}`}
    </span>
  );
}

function sourceIconUrl(source: SourcePanel): string | null {
  if (!isValidUrl(source.homepageUrl)) return null;
  return `https://www.google.com/s2/favicons?sz=64&domain_url=${encodeURIComponent(source.homepageUrl ?? '')}`;
}

function sourceAnchorId(sourceId: string): string {
  return `source-${sourceId}`;
}

function SourceIcon({ source }: { source: SourcePanel }) {
  const icon = sourceIconUrl(source);
  const fallback = source.name.trim().slice(0, 1).toUpperCase();

  return (
    <span className="source-icon" aria-hidden="true">
      <span className="source-icon-fallback">{fallback}</span>
      {icon ? (
        <img
          src={icon}
          alt=""
          loading="lazy"
          onError={(event) => {
            event.currentTarget.style.display = 'none';
          }}
        />
      ) : null}
    </span>
  );
}

function ItemTitle({ item }: { item: HotItem }) {
  const title = <HighlightedText text={item.title} keywords={item.matchedKeywords} />;
  if (!isValidUrl(item.url)) return <span className="item-title inert">{title}</span>;
  return (
    <a className="item-title" href={item.url ?? ''} target="_blank" rel="noopener noreferrer">
      {title}
    </a>
  );
}

function HotItemRow({ item }: { item: HotItem }) {
  return (
    <li className={item.matchedKeywords.length ? 'hot-item watched' : 'hot-item'}>
      <div className="item-rank">{item.rank ?? ''}</div>
      <div className="item-body">
        <ItemTitle item={item} />
        <div className="item-meta">
          <span>{item.sourceName}</span>
          {item.heat ? <span>{item.heat}</span> : null}
          <span>{formatTime(item.publishedAt || item.fetchedAt)}</span>
          {item.matchedKeywords.length ? (
            <span className="keywords">{item.matchedKeywords.join(', ')}</span>
          ) : null}
          <SignalBadge item={item} />
        </div>
        {item.summary ? (
          <p className="summary">
            <HighlightedText text={item.summary} keywords={item.matchedKeywords} />
          </p>
        ) : null}
      </div>
    </li>
  );
}

function SourceCard({ source }: { source: SourcePanel }) {
  const visibleItems = source.items.slice(0, 5);

  return (
    <article className="source-card" id={sourceAnchorId(source.id)}>
      <header className="source-header">
        <div className="source-heading">
          <SourceIcon source={source} />
          <div>
            <div className="source-title-row">
              <h3>{source.name}</h3>
              <StatusPill status={source.currentStatus} />
            </div>
            <p>
              Last success {formatTime(source.lastSuccessAt)}
              {source.hiddenLowSignalCount ? (
                <span className="low-signal-note"> · {source.hiddenLowSignalCount} low hidden</span>
              ) : null}
            </p>
          </div>
        </div>
        {isValidUrl(source.homepageUrl) ? (
          <a className="source-link" href={source.homepageUrl ?? ''} target="_blank" rel="noopener noreferrer">
            Source
          </a>
        ) : null}
      </header>

      {visibleItems.length ? (
        <ol className="hot-list">
          {visibleItems.map((item) => (
            <HotItemRow key={`${item.source}-${item.id}`} item={item} />
          ))}
        </ol>
      ) : (
        <div className="empty-state">
          {source.hiddenLowSignalCount ? 'Low-signal items hidden' : '暂无数据'}
        </div>
      )}
    </article>
  );
}

function SourceJumpBar({ sources }: { sources: SourcePanel[] }) {
  function jumpTo(sourceId: string) {
    const target = document.getElementById(sourceAnchorId(sourceId));
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className="source-jump-bar" aria-label="Source navigation">
      {sources.map((source) => (
        <button
          className="source-jump-chip"
          key={source.id}
          type="button"
          onClick={() => jumpTo(source.id)}
        >
          {source.name}
        </button>
      ))}
    </div>
  );
}

function DashboardPage({ go }: { go: (page: Page) => void }) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshState, setRefreshState] = useState('');
  const [error, setError] = useState('');
  const navigationSources = data?.sections.flatMap((section) => section.sources) ?? [];

  async function load() {
    setError('');
    try {
      const response = await fetchDashboard();
      setData(response);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Dashboard request failed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 30 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, []);

  async function refresh() {
    setRefreshState('Refreshing');
    const response = await triggerRefresh();
    if (!response.accepted) {
      setRefreshState(`Cooldown ${response.retryAfterSeconds ?? 0}s`);
      return;
    }
    setRefreshState('Refresh started');
    window.setTimeout(() => void load(), 1500);
  }

  return (
    <>
      <Toolbar
        active="dashboard"
        go={go}
        lastRefreshAt={data?.lastRefreshAt}
        onRefresh={() => void refresh()}
        refreshState={refreshState}
        sourceNavigation={navigationSources}
      />
      <main className="page-shell">
        {error ? <div className="banner">{error}</div> : null}
        {loading && !data ? <div className="loading">Loading HotRadar</div> : null}
        {data ? (
          <>
            {data.sections.map((section) => (
              <section className="theme-section" key={section.id}>
                <div className="section-heading">
                  <h2>{section.title}</h2>
                  <span>{section.sources.length} sources</span>
                </div>
                <div className="source-grid">
                  {section.sources.map((source) => (
                    <SourceCard source={source} key={source.id} />
                  ))}
                </div>
              </section>
            ))}
          </>
        ) : null}
      </main>
    </>
  );
}

function Toolbar({
  active,
  go,
  lastRefreshAt,
  onRefresh,
  refreshState,
  sourceNavigation,
}: {
  active: Page;
  go: (page: Page) => void;
  lastRefreshAt?: string | null;
  onRefresh?: () => void;
  refreshState?: string;
  sourceNavigation?: SourcePanel[];
}) {
  return (
    <header className="toolbar-shell">
      <div className="toolbar">
        <div className="brand">
          <strong>HotRadar</strong>
          <span>Last refresh {formatTime(lastRefreshAt)}</span>
        </div>
        <nav>
          <button className={active === 'dashboard' ? 'active' : ''} type="button" onClick={() => go('dashboard')}>
            Dashboard
          </button>
          <button className={active === 'history' ? 'active' : ''} type="button" onClick={() => go('history')}>
            History
          </button>
          <button className={active === 'debug' ? 'active' : ''} type="button" onClick={() => go('debug')}>
            Debug
          </button>
          {onRefresh ? (
            <button className="primary" type="button" onClick={onRefresh}>
              Refresh
            </button>
          ) : null}
        </nav>
        {refreshState ? <span className="refresh-state">{refreshState}</span> : null}
      </div>
      {sourceNavigation?.length ? <SourceJumpBar sources={sourceNavigation} /> : null}
    </header>
  );
}

function HistoryPage({ go }: { go: (page: Page) => void }) {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [sources, setSources] = useState<DebugSource[]>([]);
  const [pagination, setPagination] = useState<{
    limit: number;
    offset: number;
    total: number;
    hasMore: boolean;
  } | null>(null);
  const [q, setQ] = useState('');
  const [source, setSource] = useState('');
  const [section, setSection] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [error, setError] = useState('');

  const sections = useMemo(
    () => Array.from(new Set(sources.map((item) => item.section))).sort(),
    [sources],
  );

  async function loadHistory(event?: FormEvent, nextOffset = 0, append = false) {
    event?.preventDefault();
    setError('');
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (source) params.set('source', source);
    if (section) params.set('section', section);
    if (start) params.set('start', start);
    if (end) params.set('end', end);
    params.set('limit', '100');
    params.set('offset', String(nextOffset));
    try {
      const response = await fetchHistory(params);
      setItems((current) => (append ? [...current, ...response.items] : response.items));
      setPagination(response.pagination);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'History request failed');
    }
  }

  useEffect(() => {
    void fetchDebugSources().then((response) => setSources(response.sources));
    void loadHistory();
  }, []);

  return (
    <>
      <Toolbar active="history" go={go} />
      <main className="page-shell">
        <form className="filter-bar" onSubmit={(event) => void loadHistory(event, 0, false)}>
          <input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Keyword" />
          <select value={source} onChange={(event) => setSource(event.target.value)}>
            <option value="">All sources</option>
            {sources.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <select value={section} onChange={(event) => setSection(event.target.value)}>
            <option value="">All sections</option>
            {sections.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <input type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} />
          <input type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} />
          <button className="primary" type="submit">
            Search
          </button>
        </form>
        {error ? <div className="banner">{error}</div> : null}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Source</th>
                <th>Section</th>
                <th>First Seen</th>
                <th>Last Seen</th>
                <th>Seen</th>
                <th>Rank</th>
                <th>Heat</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    {isValidUrl(item.url) ? (
                      <a href={item.url ?? ''} target="_blank" rel="noopener noreferrer">
                        {item.title}
                      </a>
                    ) : (
                      item.title
                    )}
                  </td>
                  <td>{item.sourceName}</td>
                  <td>{item.section}</td>
                  <td>{formatTime(item.firstSeenAt)}</td>
                  <td>{formatTime(item.lastSeenAt)}</td>
                  <td>{item.seenCount}</td>
                  <td>{item.latestRank ?? ''}</td>
                  <td>{item.latestHeat ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {pagination ? (
          <div className="pagination-bar">
            <span>
              Showing {items.length} of {pagination.total}
            </span>
            <button
              type="button"
              disabled={!pagination.hasMore}
              onClick={() => void loadHistory(undefined, pagination.offset + pagination.limit, true)}
            >
              Load more
            </button>
          </div>
        ) : null}
      </main>
    </>
  );
}

function DebugPage({ go }: { go: (page: Page) => void }) {
  const [sources, setSources] = useState<DebugSource[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDebugSources()
      .then((response) => setSources(response.sources))
      .catch((exc) => setError(exc instanceof Error ? exc.message : 'Debug request failed'));
  }, []);

  return (
    <>
      <Toolbar active="debug" go={go} />
      <main className="page-shell">
        {error ? <div className="banner">{error}</div> : null}
        <div className="table-wrap debug-table">
          <table>
            <thead>
              <tr>
                <th>Source Name</th>
                <th>Section</th>
                <th>Last Fetch</th>
                <th>Last Success</th>
                <th>Last Failure</th>
                <th>Status</th>
                <th>Items</th>
                <th>Failures</th>
                <th>Error Type</th>
                <th>HTTP</th>
                <th>Error Message</th>
                <th>Avg Duration</th>
                <th>Trigger</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>{source.name}</td>
                  <td>{source.section}</td>
                  <td>{formatTime(source.lastFetchAt)}</td>
                  <td>{formatTime(source.lastSuccessAt)}</td>
                  <td>{formatTime(source.lastFailureAt)}</td>
                  <td>
                    <StatusPill status={source.currentStatus} />
                  </td>
                  <td>{source.itemsFetched}</td>
                  <td>{source.consecutiveFailures}</td>
                  <td>{source.latestErrorType ?? ''}</td>
                  <td>{source.latestHttpStatus ?? ''}</td>
                  <td className="error-cell">{source.latestErrorMessage ?? ''}</td>
                  <td>{source.averageDurationMs ? `${Math.round(source.averageDurationMs)}ms` : ''}</td>
                  <td>{source.lastRunTrigger ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromPath);

  useEffect(() => {
    const listener = () => setPage(pageFromPath());
    window.addEventListener('popstate', listener);
    return () => window.removeEventListener('popstate', listener);
  }, []);

  function go(next: Page) {
    window.history.pushState({}, '', PAGE_PATH[next]);
    setPage(next);
  }

  if (page === 'history') return <HistoryPage go={go} />;
  if (page === 'debug') return <DebugPage go={go} />;
  return <DashboardPage go={go} />;
}
