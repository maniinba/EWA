"""Persist parsed EWA reports into the database.

Shared by the manual-upload path and the SAP for Me auto-fetch path so both
produce identical, normalised records.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    Alert,
    RatingHistory,
    Report,
    Severity,
    System,
    UploadMethod,
)
from app.services.pdf_parser import ParsedReport


def get_or_create_system(db: Session, sid: str, system_type: str | None = None) -> System:
    system = db.scalar(select(System).where(System.sid == sid))
    if system is None:
        system = System(sid=sid, system_type=system_type)
        db.add(system)
        db.flush()
    elif system_type and not system.system_type:
        system.system_type = system_type
    return system


class DuplicateReportError(ValueError):
    def __init__(self, sid: str, report_date: date):
        super().__init__(f"A report for {sid} on {report_date} already exists")
        self.sid = sid
        self.report_date = report_date


def _to_severity(value: str | None) -> Severity:
    try:
        return Severity(value)
    except (ValueError, TypeError):
        return Severity.yellow


def persist_report(
    db: Session,
    parsed: ParsedReport,
    *,
    file_name: str | None = None,
    file_path: str | None = None,
    file_size: int | None = None,
    upload_method: UploadMethod = UploadMethod.manual,
    override_sid: str | None = None,
    override_date: date | None = None,
    allow_replace: bool = False,
) -> Report:
    """Create a Report (plus its alerts and rating history) from parsed data."""
    sid = override_sid or parsed.sid
    report_date = override_date or parsed.report_date
    if not sid:
        raise ValueError("Could not determine system SID from the report")
    if not report_date:
        raise ValueError("Could not determine report date from the report")

    system = get_or_create_system(db, sid, parsed.system_type)

    existing = db.scalar(
        select(Report).where(
            Report.system_id == system.id, Report.report_date == report_date
        )
    )
    if existing:
        if not allow_replace:
            raise DuplicateReportError(sid, report_date)
        db.delete(existing)
        db.flush()

    overall = _to_severity(parsed.overall_rating) if parsed.overall_rating else None
    report = Report(
        system_id=system.id,
        report_date=report_date,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        upload_method=upload_method,
        overall_rating=overall,
        parsed_data=parsed.to_dict(),
    )
    db.add(report)
    db.flush()

    for pr in parsed.ratings:
        db.add(
            RatingHistory(
                system_id=system.id,
                report_id=report.id,
                report_date=report_date,
                chapter=pr.chapter,
                rating=_to_severity(pr.rating),
                score=pr.score,
            )
        )

    for pa in parsed.alerts:
        db.add(
            Alert(
                report_id=report.id,
                system_id=system.id,
                chapter=pa.chapter,
                severity=_to_severity(pa.severity),
                title=pa.title,
                description=pa.description,
                recommendation=pa.recommendation,
                sap_note_refs=pa.sap_note_refs or [],
                tags=pa.tags or [],
            )
        )

    system.last_report_date = max(
        report_date, system.last_report_date or report_date
    )
    db.flush()
    return report
