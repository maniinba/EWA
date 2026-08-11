"""Report upload, parsing preview, listing and detail endpoints."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, write_audit
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Report, System, UploadMethod, User, UserRole
from app.schemas.schemas import (
    ParsePreview,
    ParsedAlert,
    RatingItem,
    ReportDetail,
    ReportOut,
)
from app.services.ingestion import DuplicateReportError, persist_report
from app.services.pdf_parser import parse_ewa_document

router = APIRouter(prefix="/reports", tags=["reports"])

_ALLOWED_EXT = (".pdf", ".doc", ".docx", ".html", ".htm", ".txt")


def _validate_upload(file: UploadFile, data: bytes) -> None:
    name = (file.filename or "").lower()
    if not name.endswith(_ALLOWED_EXT):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(_ALLOWED_EXT)}",
        )
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit"
        )


def _to_preview(parsed) -> ParsePreview:
    return ParsePreview(
        sid=parsed.sid,
        report_date=parsed.report_date,
        system_type=parsed.system_type,
        overall_rating=parsed.overall_rating,
        ratings=[RatingItem(chapter=r.chapter, rating=r.rating, score=r.score) for r in parsed.ratings],
        alerts=[
            ParsedAlert(
                chapter=a.chapter,
                severity=a.severity,
                title=a.title,
                description=a.description,
                recommendation=a.recommendation,
                sap_note_refs=a.sap_note_refs,
                tags=a.tags,
            )
            for a in parsed.alerts
        ],
        alert_count=len(parsed.alerts),
    )


@router.post("/preview", response_model=ParsePreview)
async def preview_report(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> ParsePreview:
    """Parse a report and return extracted data WITHOUT persisting it."""
    data = await file.read()
    _validate_upload(file, data)
    parsed = parse_ewa_document(data, file.filename or "")
    return _to_preview(parsed)


@router.post("/upload", response_model=ReportDetail, status_code=201)
async def upload_report(
    file: UploadFile = File(...),
    sid: str | None = Form(default=None),
    report_date: date | None = Form(default=None),
    replace_existing: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.operator)),
) -> ReportDetail:
    """Upload, parse and persist a single EWA report.

    ``sid`` and ``report_date`` form fields override values detected from the
    document (useful when parsing cannot determine them).
    """
    data = await file.read()
    _validate_upload(file, data)
    parsed = parse_ewa_document(data, file.filename or "")

    # Persist the raw file to disk for later download / re-parsing.
    file_path = None
    try:
        dest = settings.upload_path / f"{uuid.uuid4()}_{file.filename}"
        dest.write_bytes(data)
        file_path = str(dest)
    except OSError:
        file_path = None  # storage optional; DB record is source of truth

    try:
        report = persist_report(
            db,
            parsed,
            file_name=file.filename,
            file_path=file_path,
            file_size=len(data),
            upload_method=UploadMethod.manual,
            override_sid=(sid.upper() if sid else None),
            override_date=report_date,
            allow_replace=replace_existing,
        )
    except DuplicateReportError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    write_audit(db, user, "upload_report", "report", str(report.id),
                {"sid": report.system.sid, "alerts": len(report.alerts)})
    db.commit()
    db.refresh(report)
    return _report_detail(report)


@router.get("", response_model=list[ReportOut])
def list_reports(
    system_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Report]:
    stmt = select(Report).order_by(Report.report_date.desc())
    if system_id:
        stmt = stmt.where(Report.system_id == system_id)
    return list(db.scalars(stmt.limit(limit).offset(offset)).all())


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReportDetail:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_detail(report)


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    write_audit(db, user, "delete_report", "report", str(report_id))
    db.commit()


def _report_detail(report: Report) -> ReportDetail:
    detail = ReportDetail.model_validate(report)
    detail.system_sid = report.system.sid if report.system else None
    return detail
