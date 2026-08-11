"""Celery tasks for asynchronous PDF parsing and scheduled SAP for Me fetch.

The API works fully without Celery (the ``/connector/fetch`` endpoint runs
synchronously). Celery is used in production to offload heavy parsing and to
run the weekly auto-fetch on a beat schedule.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "ewa",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={
        "weekly-ewa-fetch": {
            "task": "app.workers.tasks.fetch_all_reports",
            # Every Monday at 06:00 UTC.
            "schedule": crontab(hour=6, minute=0, day_of_week=1),
        }
    },
)


@celery_app.task(name="app.workers.tasks.fetch_all_reports")
def fetch_all_reports() -> dict:
    """Scheduled auto-fetch of EWA reports for all registered systems."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.models import ConnectorConfig, System, UploadMethod
    from app.services.ingestion import persist_report
    from app.services.pdf_parser import parse_ewa_document
    from app.services.sapforme import ConnectorError, client_from_config

    with SessionLocal() as db:
        cfg = db.scalar(select(ConnectorConfig).where(ConnectorConfig.name == "default"))
        client = client_from_config(cfg)
        if not client or not cfg.enabled:
            return {"skipped": "connector not enabled"}

        imported = 0
        errors: list[str] = []
        for system in db.scalars(select(System)).all():
            try:
                for meta in client.list_reports(system.sid):
                    ref = meta.get("id") or meta.get("reportId")
                    if not ref:
                        continue
                    data = client.download_report(ref)
                    parsed = parse_ewa_document(data, f"{system.sid}.pdf")
                    persist_report(
                        db, parsed, file_name=f"{system.sid}_{ref}.pdf",
                        file_size=len(data), upload_method=UploadMethod.auto_fetch,
                        override_sid=system.sid, allow_replace=True,
                    )
                    imported += 1
            except ConnectorError as exc:
                errors.append(f"{system.sid}: {exc}")

        cfg.last_sync_at = datetime.now(timezone.utc)
        cfg.last_sync_status = "error" if errors else "ok"
        cfg.last_sync_message = "; ".join(errors) if errors else f"Imported {imported}"
        db.commit()
        return {"imported": imported, "errors": errors}
