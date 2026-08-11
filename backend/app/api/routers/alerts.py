"""Alert listing, filtering, status tracking and similarity endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, write_audit
from app.core.database import get_db
from app.models.models import (
    Alert,
    AlertStatus,
    Report,
    Severity,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import AlertStatusUpdate, AlertWithContext

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _with_context(db: Session, alert: Alert) -> AlertWithContext:
    item = AlertWithContext.model_validate(alert)
    system = db.get(System, alert.system_id)
    report = db.get(Report, alert.report_id)
    item.system_sid = system.sid if system else None
    item.report_date = report.report_date if report else None
    return item


@router.get("", response_model=list[AlertWithContext])
def list_alerts(
    system_id: uuid.UUID | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    chapter: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlertWithContext]:
    stmt = select(Alert)
    if system_id:
        stmt = stmt.where(Alert.system_id == system_id)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if status:
        stmt = stmt.where(Alert.status == status)
    if chapter:
        stmt = stmt.where(Alert.chapter.ilike(f"%{chapter}%"))

    # Order by severity (red first) then most recent.
    severity_rank = {Severity.red: 0, Severity.yellow: 1, Severity.green: 2, Severity.gray: 3}
    alerts = list(db.scalars(stmt).all())
    if tag:
        alerts = [a for a in alerts if a.tags and tag in a.tags]
    alerts.sort(key=lambda a: (severity_rank.get(a.severity, 9), a.created_at.timestamp() * -1))
    alerts = alerts[offset : offset + limit]
    return [_with_context(db, a) for a in alerts]


@router.get("/{alert_id}", response_model=AlertWithContext)
def get_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertWithContext:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _with_context(db, alert)


@router.get("/{alert_id}/similar", response_model=list[AlertWithContext])
def similar_alerts(
    alert_id: uuid.UUID,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlertWithContext]:
    """Find recurring/related alerts across systems by keyword overlap."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    keywords = {w.lower() for w in alert.title.split() if len(w) > 3}
    candidates = db.scalars(select(Alert).where(Alert.id != alert_id)).all()

    def score(other: Alert) -> int:
        other_words = {w.lower() for w in other.title.split() if len(w) > 3}
        overlap = len(keywords & other_words)
        if alert.chapter and other.chapter == alert.chapter:
            overlap += 1
        return overlap

    ranked = sorted(candidates, key=score, reverse=True)
    ranked = [a for a in ranked if score(a) > 0][:limit]
    return [_with_context(db, a) for a in ranked]


@router.patch("/{alert_id}/status", response_model=AlertWithContext)
def update_alert_status(
    alert_id: uuid.UUID,
    payload: AlertStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.operator)),
) -> AlertWithContext:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    old_status = alert.status
    alert.status = payload.status
    if payload.resolution_notes is not None:
        alert.resolution_notes = payload.resolution_notes
    alert.resolved_at = (
        datetime.now(timezone.utc) if payload.status == AlertStatus.resolved else None
    )
    write_audit(
        db, user, "update_alert_status", "alert", str(alert_id),
        {"from": old_status.value, "to": payload.status.value},
    )
    db.commit()
    db.refresh(alert)
    return _with_context(db, alert)
