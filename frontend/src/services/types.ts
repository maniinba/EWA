export type Severity = 'red' | 'yellow' | 'green' | 'gray';
export type Rating = 'red' | 'yellow' | 'green' | 'gray';
export type AlertStatus = 'open' | 'in_progress' | 'resolved' | 'deferred';
export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SeverityBreakdown {
  red: number;
  yellow: number;
  green: number;
  gray: number;
}

export interface StatusBreakdown {
  open: number;
  in_progress: number;
  resolved: number;
  deferred: number;
}

export interface DashboardSummary {
  total_systems: number;
  total_reports: number;
  total_alerts: number;
  open_alerts: number;
  critical_alerts: number;
  resolved_alerts: number;
  severity_breakdown: SeverityBreakdown;
  status_breakdown: StatusBreakdown;
}

export interface SystemItem {
  id: number;
  sid: string;
  description: string | null;
  system_type: string | null;
  landscape: string | null;
  last_report_date: string | null;
  created_at: string;
  report_count: number;
  open_alerts: number;
  critical_alerts: number;
  latest_rating: Rating | null;
}

export interface CreateSystemPayload {
  sid: string;
  description?: string;
  system_type?: string;
  landscape?: string;
}

export interface Alert {
  id: number;
  report_id: number;
  system_id: number;
  chapter: string;
  severity: Severity;
  title: string;
  description: string | null;
  recommendation: string | null;
  sap_note_refs: string[];
  tags: string[];
  status: AlertStatus;
  resolution_notes: string | null;
  resolved_at: string | null;
  created_at: string;
  system_sid: string;
  report_date: string | null;
}

export interface AlertFilters {
  system_id?: number;
  severity?: Severity;
  status?: AlertStatus;
  chapter?: string;
  tag?: string;
  limit?: number;
  offset?: number;
}

export interface UpdateAlertStatusPayload {
  status: AlertStatus;
  resolution_notes?: string;
}

export interface Report {
  id: number;
  system_id: number;
  report_date: string;
  file_name: string;
  file_size: number;
  upload_method: string;
  overall_rating: Rating | null;
  created_at: string;
}

export interface ReportDetail extends Report {
  system_sid: string;
  alerts: Alert[];
  parsed_data: unknown;
}

export interface PreviewRating {
  chapter: string;
  rating: Rating;
  score: number | null;
}

export interface PreviewAlert {
  chapter: string;
  severity: Severity;
  title: string;
  description: string | null;
  recommendation: string | null;
  sap_note_refs: string[];
  tags: string[];
}

export interface ReportPreview {
  sid: string;
  report_date: string;
  system_type: string | null;
  overall_rating: Rating | null;
  ratings: PreviewRating[];
  alerts: PreviewAlert[];
  alert_count: number;
}

export interface AlertTrendPoint {
  report_date: string;
  red: number;
  yellow: number;
  green: number;
  total: number;
  overall_rating: Rating | null;
}

export interface ChapterTrendPoint {
  report_date: string;
  rating: Rating | null;
  score: number | null;
}

export interface ChapterTrend {
  chapter: string;
  points: ChapterTrendPoint[];
}

export interface Trends {
  system_id: number;
  system_sid: string;
  alert_trend: AlertTrendPoint[];
  chapter_trends: ChapterTrend[];
}

export interface RatingChange {
  chapter: string;
  from: Rating | null;
  to: Rating | null;
  direction: 'better' | 'worse' | 'same' | string;
}

export interface WhatChanged {
  system_id: number;
  from_date: string | null;
  to_date: string | null;
  new_alerts: string[];
  resolved_alerts: string[];
  rating_changes: RatingChange[];
}

export interface SearchResult {
  alerts: Alert[];
  total: number;
}

export interface ConnectorStatus {
  configured: boolean;
  enabled: boolean;
  s_user: string | null;
  last_sync_at: string | null;
  last_sync_status: string | null;
  last_sync_message: string | null;
}

export interface ConnectorConfigPayload {
  client_id?: string;
  client_secret?: string;
  s_user?: string;
  s_password?: string;
  enabled: boolean;
}

export interface ConnectorActionResult {
  [key: string]: unknown;
}
