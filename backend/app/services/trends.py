"""Trend analysis and 'what changed' comparison between report versions."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Alert, RatingHistory, Report, Severity, System
from app.schemas.schemas import (
    ChapterTrend,
    TrendPoint,
    TrendResponse,
    WhatChanged,
)

_SCORE = {Severity.red: 3, Severity.yellow: 2, Severity.green: 1, Severity.gray: 0}


def build_trends(db: Session, system: System) -> TrendResponse:
    """Assemble alert-count and per-chapter rating trends for a system."""
    reports = db.scalars(
        select(Report).where(Report.system_id == system.id).order_by(Report.report_date)
    ).all()

    alert_trend: list[TrendPoint] = []
    for report in reports:
        counts = {"red": 0, "yellow": 0, "green": 0, "gray": 0}
        for alert in report.alerts:
            counts[alert.severity.value] = counts.get(alert.severity.value, 0) + 1
        alert_trend.append(
            TrendPoint(
                report_date=report.report_date,
                red=counts["red"],
                yellow=counts["yellow"],
                green=counts["green"],
                total=sum(counts.values()),
                overall_rating=report.overall_rating,
            )
        )

    # Per-chapter rating history → numeric score series.
    ratings = db.scalars(
        select(RatingHistory)
        .where(RatingHistory.system_id == system.id)
        .order_by(RatingHistory.report_date)
    ).all()
    by_chapter: dict[str, list[dict]] = defaultdict(list)
    for r in ratings:
        by_chapter[r.chapter].append(
            {
                "report_date": r.report_date.isoformat(),
                "rating": r.rating.value,
                "score": r.score,
            }
        )
    chapter_trends = [
        ChapterTrend(chapter=chapter, points=points)
        for chapter, points in sorted(by_chapter.items())
    ]

    return TrendResponse(
        system_id=system.id,
        system_sid=system.sid,
        alert_trend=alert_trend,
        chapter_trends=chapter_trends,
    )


def what_changed(db: Session, system: System) -> WhatChanged:
    """Diff the two most recent reports for a system."""
    reports = db.scalars(
        select(Report)
        .where(Report.system_id == system.id)
        .order_by(Report.report_date.desc())
        .limit(2)
    ).all()

    if len(reports) < 2:
        latest = reports[0] if reports else None
        return WhatChanged(
            system_id=system.id,
            from_date=None,
            to_date=latest.report_date if latest else None,
            new_alerts=[a.title for a in latest.alerts] if latest else [],
        )

    current, previous = reports[0], reports[1]
    cur_titles = {a.title for a in current.alerts}
    prev_titles = {a.title for a in previous.alerts}

    new_alerts = sorted(cur_titles - prev_titles)
    resolved_alerts = sorted(prev_titles - cur_titles)

    # Rating changes per chapter.
    def rating_map(report: Report) -> dict[str, Severity]:
        rows = db.scalars(
            select(RatingHistory).where(RatingHistory.report_id == report.id)
        ).all()
        return {r.chapter: r.rating for r in rows}

    cur_ratings = rating_map(current)
    prev_ratings = rating_map(previous)
    rating_changes = []
    for chapter, cur in cur_ratings.items():
        prev = prev_ratings.get(chapter)
        if prev and prev != cur:
            direction = "worse" if _SCORE[cur] > _SCORE[prev] else "better"
            rating_changes.append(
                {"chapter": chapter, "from": prev.value, "to": cur.value, "direction": direction}
            )

    return WhatChanged(
        system_id=system.id,
        from_date=previous.report_date,
        to_date=current.report_date,
        new_alerts=new_alerts,
        resolved_alerts=resolved_alerts,
        rating_changes=rating_changes,
    )
