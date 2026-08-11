"""SQLAlchemy ORM models for the EWA Dashboard."""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base, PortableJSON, gen_uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, enum.Enum):
    red = "red"
    yellow = "yellow"
    green = "green"
    gray = "gray"


class AlertStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    deferred = "deferred"


class UploadMethod(str, enum.Enum):
    manual = "manual"
    auto_fetch = "auto_fetch"


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class System(Base):
    __tablename__ = "systems"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    sid: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    landscape: Mapped[str | None] = mapped_column(String(50), nullable=True)  # PROD/QA/DEV
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_report_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    reports: Mapped[list[Report]] = relationship(
        back_populates="system", cascade="all, delete-orphan"
    )
    ratings: Mapped[list[RatingHistory]] = relationship(
        back_populates="system", cascade="all, delete-orphan"
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("system_id", "report_date", name="uq_report_system_date"),)

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    system_id: Mapped[str] = mapped_column(GUID, ForeignKey("systems.id", ondelete="CASCADE"))
    report_date: Mapped[date] = mapped_column(Date, index=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_method: Mapped[UploadMethod] = mapped_column(
        Enum(UploadMethod), default=UploadMethod.manual
    )
    overall_rating: Mapped[Severity | None] = mapped_column(Enum(Severity), nullable=True)
    parsed_data: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    system: Mapped[System] = relationship(back_populates="reports")
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    report_id: Mapped[str] = mapped_column(GUID, ForeignKey("reports.id", ondelete="CASCADE"))
    system_id: Mapped[str] = mapped_column(GUID, ForeignKey("systems.id", ondelete="CASCADE"), index=True)
    chapter: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), default=Severity.yellow, index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    sap_note_refs: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.open, index=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped[Report] = relationship(back_populates="alerts")


class RatingHistory(Base):
    __tablename__ = "ratings_history"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    system_id: Mapped[str] = mapped_column(GUID, ForeignKey("systems.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("reports.id", ondelete="CASCADE"), nullable=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    chapter: Mapped[str] = mapped_column(String(150))
    rating: Mapped[Severity] = mapped_column(Enum(Severity))
    score: Mapped[int] = mapped_column(Integer, default=0)

    system: Mapped[System] = relationship(back_populates="ratings")


class ConnectorConfig(Base):
    """SAP for Me connector configuration. Secrets stored encrypted."""

    __tablename__ = "connector_config"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), default="default", unique=True)
    client_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    s_user: Mapped[str | None] = mapped_column(String(50), nullable=True)
    s_password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_sync_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.viewer)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=gen_uuid)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detail: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
