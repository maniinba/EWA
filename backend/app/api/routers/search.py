"""Full-text search and dashboard summary endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    Alert,
    AlertStatus,
    Report,
    Severity,
    System,
    User,
)
from app.schemas.schemas import (
    AlertWithContext,
    DashboardSummary,
    SearchResult,
)

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResult)
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SearchResult:
    pattern = f"%{q}%"
    stmt = select(Alert).where(
        or_(
            Alert.title.ilike(pattern),
            Alert.description.ilike(pattern),
            Alert.recommendation.ilike(pattern),
            Alert.chapter.ilike(pattern),
        )
    )
    alerts = list(db.scalars(stmt).all())
    total = len(alerts)

    # Attach system/report context.
    sid_map = {s.id: s.sid for s in db.scalars(select(System)).all()}
    date_map = {r.id: r.report_date for r in db.scalars(select(Report)).all()}
    results = []
    for a in alerts[:limit]:
        item = AlertWithContext.model_validate(a)
        item.system_sid = sid_map.get(a.system_id)
        item.report_date = date_map.get(a.report_id)
        results.append(item)
    return SearchResult(alerts=results, total=total)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> DashboardSummary:
    total_systems = db.scalar(select(func.count(System.id))) or 0
    total_reports = db.scalar(select(func.count(Report.id))) or 0
    total_alerts = db.scalar(select(func.count(Alert.id))) or 0

    severity_breakdown = {s.value: 0 for s in Severity}
    for sev, count in db.execute(
        select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
    ).all():
        severity_breakdown[sev.value] = count

    status_breakdown = {s.value: 0 for s in AlertStatus}
    for st, count in db.execute(
        select(Alert.status, func.count(Alert.id)).group_by(Alert.status)
    ).all():
        status_breakdown[st.value] = count

    open_alerts = total_alerts - status_breakdown.get("resolved", 0)
    critical_alerts = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.severity == Severity.red, Alert.status != AlertStatus.resolved
        )
    ) or 0

    return DashboardSummary(
        total_systems=total_systems,
        total_reports=total_reports,
        total_alerts=total_alerts,
        open_alerts=open_alerts,
        critical_alerts=critical_alerts,
        resolved_alerts=status_breakdown.get("resolved", 0),
        severity_breakdown=severity_breakdown,
        status_breakdown=status_breakdown,
    )
