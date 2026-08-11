"""Pydantic request/response schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.models import (
    AlertStatus,
    Severity,
    UploadMethod,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    full_name: str | None = None
    role: UserRole = UserRole.viewer


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool


# --------------------------------------------------------------------------- #
# Systems
# --------------------------------------------------------------------------- #
class SystemCreate(BaseModel):
    sid: str = Field(min_length=1, max_length=10)
    description: str | None = None
    system_type: str | None = None
    landscape: str | None = None


class SystemUpdate(BaseModel):
    description: str | None = None
    system_type: str | None = None
    landscape: str | None = None


class SystemOut(ORMModel):
    id: uuid.UUID
    sid: str
    description: str | None
    system_type: str | None
    landscape: str | None
    last_report_date: date | None
    created_at: datetime


class SystemWithStats(SystemOut):
    report_count: int = 0
    open_alerts: int = 0
    critical_alerts: int = 0
    latest_rating: Severity | None = None


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
class AlertOut(ORMModel):
    id: uuid.UUID
    report_id: uuid.UUID
    system_id: uuid.UUID
    chapter: str | None
    severity: Severity
    title: str
    description: str | None
    recommendation: str | None
    sap_note_refs: list[str] | None
    tags: list[str] | None
    status: AlertStatus
    resolution_notes: str | None
    resolved_at: datetime | None
    created_at: datetime


class AlertWithContext(AlertOut):
    system_sid: str | None = None
    report_date: date | None = None


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    resolution_notes: str | None = None


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
class ReportOut(ORMModel):
    id: uuid.UUID
    system_id: uuid.UUID
    report_date: date
    file_name: str | None
    file_size: int | None
    upload_method: UploadMethod
    overall_rating: Severity | None
    created_at: datetime


class ReportDetail(ReportOut):
    system_sid: str | None = None
    alerts: list[AlertOut] = []
    parsed_data: dict | None = None


class ParsePreview(BaseModel):
    """Result of parsing without persisting."""

    sid: str | None
    report_date: date | None
    system_type: str | None
    overall_rating: Severity | None
    ratings: list[RatingItem] = []
    alerts: list[ParsedAlert] = []
    alert_count: int = 0


class RatingItem(BaseModel):
    chapter: str
    rating: Severity
    score: int = 0


class ParsedAlert(BaseModel):
    chapter: str | None = None
    severity: Severity = Severity.yellow
    title: str
    description: str | None = None
    recommendation: str | None = None
    sap_note_refs: list[str] = []
    tags: list[str] = []


# --------------------------------------------------------------------------- #
# Trends
# --------------------------------------------------------------------------- #
class TrendPoint(BaseModel):
    report_date: date
    red: int = 0
    yellow: int = 0
    green: int = 0
    total: int = 0
    overall_rating: Severity | None = None


class ChapterTrend(BaseModel):
    chapter: str
    points: list[dict]


class TrendResponse(BaseModel):
    system_id: uuid.UUID
    system_sid: str
    alert_trend: list[TrendPoint] = []
    chapter_trends: list[ChapterTrend] = []


class WhatChanged(BaseModel):
    system_id: uuid.UUID
    from_date: date | None
    to_date: date | None
    new_alerts: list[str] = []
    resolved_alerts: list[str] = []
    rating_changes: list[dict] = []


# --------------------------------------------------------------------------- #
# Connector
# --------------------------------------------------------------------------- #
class ConnectorConfigIn(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    s_user: str | None = None
    s_password: str | None = None
    enabled: bool = False


class ConnectorStatus(BaseModel):
    configured: bool
    enabled: bool
    s_user: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_message: str | None = None


# --------------------------------------------------------------------------- #
# Search & dashboard summary
# --------------------------------------------------------------------------- #
class SearchResult(BaseModel):
    alerts: list[AlertWithContext] = []
    total: int = 0


class DashboardSummary(BaseModel):
    total_systems: int
    total_reports: int
    total_alerts: int
    open_alerts: int
    critical_alerts: int
    resolved_alerts: int
    severity_breakdown: dict[str, int]
    status_breakdown: dict[str, int]


# Resolve forward references for nested models.
ParsePreview.model_rebuild()
