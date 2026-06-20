export type HotItem = {
  id: number | string;
  source: string;
  sourceName: string;
  section: string;
  title: string;
  url?: string | null;
  rank?: number | null;
  heat?: string | null;
  summary?: string | null;
  author?: string | null;
  publishedAt?: string | null;
  fetchedAt: string;
  matchedKeywords: string[];
  extra?: Record<string, unknown>;
};

export type SignalLevel = 'high' | 'medium' | 'low';

export type SourcePanel = {
  id: string;
  name: string;
  section: string;
  displayType: 'feed' | 'ranking';
  homepageUrl?: string | null;
  lastSuccessAt?: string | null;
  lastFetchAt?: string | null;
  currentStatus: 'never_fetched' | 'success' | 'degraded' | 'failed';
  hiddenLowSignalCount?: number;
  items: HotItem[];
};

export type DashboardSection = {
  id: string;
  title: string;
  sources: SourcePanel[];
};

export type DashboardResponse = {
  generatedAt: string;
  lastRefreshAt?: string | null;
  refreshJob?: RefreshJob | null;
  myWatch: {
    id: string;
    title: string;
    items: HotItem[];
  };
  sections: DashboardSection[];
};

export type RefreshResponse = {
  accepted: boolean;
  status: string;
  jobId?: string;
  retryAfterSeconds?: number;
};

export type RefreshJob = {
  jobId: string;
  status: string;
  trigger: string;
  force: boolean;
  requestedAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  summary?: Record<string, unknown> | null;
};

export type HistoryItem = {
  id: number;
  title: string;
  source: string;
  sourceName: string;
  section: string;
  firstSeenAt: string;
  lastSeenAt: string;
  seenCount: number;
  latestRank?: number | null;
  latestHeat?: string | null;
  url?: string | null;
};

export type HistoryResponse = {
  items: HistoryItem[];
  pagination: {
    limit: number;
    offset: number;
    total: number;
    hasMore: boolean;
  };
};

export type DebugSource = {
  id: string;
  name: string;
  section: string;
  displayType: string;
  homepageUrl?: string | null;
  lastFetchAt?: string | null;
  lastSuccessAt?: string | null;
  lastFailureAt?: string | null;
  currentStatus: 'never_fetched' | 'success' | 'degraded' | 'failed';
  itemsFetched: number;
  consecutiveFailures: number;
  latestErrorType?: string | null;
  latestHttpStatus?: number | null;
  latestErrorMessage?: string | null;
  averageDurationMs?: number | null;
  lastRunTrigger?: string | null;
};

export type DebugResponse = {
  sources: DebugSource[];
};
