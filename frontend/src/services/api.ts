import axios, { AxiosError } from 'axios';
import type {
  Alert,
  AlertFilters,
  ConnectorActionResult,
  ConnectorConfigPayload,
  ConnectorStatus,
  CreateSystemPayload,
  DashboardSummary,
  Report,
  ReportDetail,
  ReportPreview,
  SearchResult,
  SystemItem,
  TokenResponse,
  Trends,
  UpdateAlertStatusPayload,
  User,
  WhatChanged,
} from './types';

export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';
const TOKEN_KEY = 'ewa_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401. We navigate via a full location change so it works
// outside React Router context (interceptors run anywhere).
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && getToken()) {
      clearToken();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  },
);

/** Extract a human-readable message from an axios error. */
export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
    if (err.message) return err.message;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export function isConflict(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response?.status === 409;
}

// ---- Auth ----
export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams();
  body.append('username', username);
  body.append('password', password);
  const { data } = await api.post<TokenResponse>('/auth/token', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

// ---- Dashboard ----
export async function fetchSummary(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>('/dashboard/summary');
  return data;
}

// ---- Systems ----
export async function fetchSystems(): Promise<SystemItem[]> {
  const { data } = await api.get<SystemItem[]>('/systems');
  return data;
}

export async function createSystem(payload: CreateSystemPayload): Promise<SystemItem> {
  const { data } = await api.post<SystemItem>('/systems', payload);
  return data;
}

// ---- Alerts ----
export async function fetchAlerts(filters: AlertFilters = {}): Promise<Alert[]> {
  const params: Record<string, string | number> = {};
  if (filters.system_id) params.system_id = filters.system_id;
  if (filters.severity) params.severity = filters.severity;
  if (filters.status) params.status = filters.status;
  if (filters.chapter) params.chapter = filters.chapter;
  if (filters.tag) params.tag = filters.tag;
  if (filters.limit != null) params.limit = filters.limit;
  if (filters.offset != null) params.offset = filters.offset;
  const { data } = await api.get<Alert[]>('/alerts', { params });
  return data;
}

export async function fetchAlert(id: string): Promise<Alert> {
  const { data } = await api.get<Alert>(`/alerts/${id}`);
  return data;
}

export async function fetchSimilarAlerts(id: string): Promise<Alert[]> {
  const { data } = await api.get<Alert[]>(`/alerts/${id}/similar`);
  return data;
}

export async function updateAlertStatus(
  id: string,
  payload: UpdateAlertStatusPayload,
): Promise<Alert> {
  const { data } = await api.patch<Alert>(`/alerts/${id}/status`, payload);
  return data;
}

// ---- Reports ----
export async function fetchReports(systemId?: string): Promise<Report[]> {
  const params: Record<string, string> = {};
  if (systemId != null) params.system_id = systemId;
  const { data } = await api.get<Report[]>('/reports', { params });
  return data;
}

export async function fetchReport(id: string): Promise<ReportDetail> {
  const { data } = await api.get<ReportDetail>(`/reports/${id}`);
  return data;
}

export async function deleteReport(id: string): Promise<void> {
  await api.delete(`/reports/${id}`);
}

export async function previewReport(file: File): Promise<ReportPreview> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<ReportPreview>('/reports/preview', form);
  return data;
}

export interface UploadReportOptions {
  sid?: string;
  reportDate?: string;
  replaceExisting?: boolean;
}

export async function uploadReport(
  file: File,
  options: UploadReportOptions = {},
): Promise<ReportDetail> {
  const form = new FormData();
  form.append('file', file);
  if (options.sid) form.append('sid', options.sid);
  if (options.reportDate) form.append('report_date', options.reportDate);
  if (options.replaceExisting != null) {
    form.append('replace_existing', String(options.replaceExisting));
  }
  const { data } = await api.post<ReportDetail>('/reports/upload', form);
  return data;
}

// ---- Trends ----
export async function fetchTrends(systemId: string): Promise<Trends> {
  const { data } = await api.get<Trends>(`/trends/${systemId}`);
  return data;
}

export async function fetchWhatChanged(systemId: string): Promise<WhatChanged> {
  const { data } = await api.get<WhatChanged>(`/trends/${systemId}/what-changed`);
  return data;
}

// ---- Search ----
export async function search(q: string): Promise<SearchResult> {
  const { data } = await api.get<SearchResult>('/search', { params: { q } });
  return data;
}

// ---- Admin ----
export interface PurgeResult {
  deleted: { alerts: number; ratings: number; reports: number; systems: number };
}

export async function purgeData(): Promise<PurgeResult> {
  const { data } = await api.post<PurgeResult>('/admin/purge');
  return data;
}

// ---- Connector ----
export async function fetchConnectorStatus(): Promise<ConnectorStatus> {
  const { data } = await api.get<ConnectorStatus>('/connector/status');
  return data;
}

export async function saveConnectorConfig(
  payload: ConnectorConfigPayload,
): Promise<ConnectorStatus> {
  const { data } = await api.post<ConnectorStatus>('/connector/config', payload);
  return data;
}

export async function testConnector(): Promise<ConnectorActionResult> {
  const { data } = await api.post<ConnectorActionResult>('/connector/test');
  return data;
}

export async function fetchConnectorNow(): Promise<ConnectorActionResult> {
  const { data } = await api.post<ConnectorActionResult>('/connector/fetch');
  return data;
}
