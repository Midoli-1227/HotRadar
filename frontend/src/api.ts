import type {
  DashboardResponse,
  DebugResponse,
  HistoryResponse,
  RefreshResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const ADMIN_TOKEN = import.meta.env.VITE_HOTRADAR_ADMIN_TOKEN ?? '';

function withAdminToken(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  if (ADMIN_TOKEN) headers.set('X-HotRadar-Admin-Token', ADMIN_TOKEN);
  return { ...init, headers };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>('/api/dashboard');
}

export function triggerRefresh(): Promise<RefreshResponse> {
  return request<RefreshResponse>('/api/refresh', withAdminToken({ method: 'POST' }));
}

export function fetchHistory(params: URLSearchParams): Promise<HistoryResponse> {
  const suffix = params.toString();
  return request<HistoryResponse>(`/api/history${suffix ? `?${suffix}` : ''}`);
}

export function fetchDebugSources(): Promise<DebugResponse> {
  return request<DebugResponse>('/api/debug/sources', withAdminToken());
}
