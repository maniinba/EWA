"""SAP for Me connector configuration and fetch endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role, write_audit
from app.core.database import get_db
from app.core.security import encrypt_secret
from app.models.models import ConnectorConfig, System, UploadMethod, User, UserRole
from app.schemas.schemas import ConnectorConfigIn, ConnectorStatus
from app.services.ingestion import persist_report
from app.services.pdf_parser import parse_ewa_document
from app.services.sapforme import ConnectorError, client_from_config

router = APIRouter(prefix="/connector", tags=["connector"])


def _get_config(db: Session) -> ConnectorConfig | None:
    return db.scalar(select(ConnectorConfig).where(ConnectorConfig.name == "default"))


@router.get("/status", response_model=ConnectorStatus)
def connector_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.operator)),
) -> ConnectorStatus:
    cfg = _get_config(db)
    if not cfg:
        return ConnectorStatus(configured=False, enabled=False)
    return ConnectorStatus(
        configured=bool(cfg.client_id and cfg.client_secret_enc),
        enabled=cfg.enabled,
        s_user=cfg.s_user,
        last_sync_at=cfg.last_sync_at,
        last_sync_status=cfg.last_sync_status,
        last_sync_message=cfg.last_sync_message,
    )


@router.post("/config", response_model=ConnectorStatus)
def configure_connector(
    payload: ConnectorConfigIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
) -> ConnectorStatus:
    cfg = _get_config(db)
    if not cfg:
        cfg = ConnectorConfig(name="default")
        db.add(cfg)

    if payload.client_id is not None:
        cfg.client_id = payload.client_id
    if payload.client_secret:
        cfg.client_secret_enc = encrypt_secret(payload.client_secret)
    if payload.s_user is not None:
        cfg.s_user = payload.s_user
    if payload.s_password:
        cfg.s_password_enc = encrypt_secret(payload.s_password)
    cfg.enabled = payload.enabled

    write_audit(db, user, "configure_connector", "connector", "default")
    db.commit()
    db.refresh(cfg)
    return ConnectorStatus(
        configured=bool(cfg.client_id and cfg.client_secret_enc),
        enabled=cfg.enabled,
        s_user=cfg.s_user,
        last_sync_at=cfg.last_sync_at,
        last_sync_status=cfg.last_sync_status,
        last_sync_message=cfg.last_sync_message,
    )


@router.post("/test", response_model=ConnectorStatus)
def test_connector(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.operator)),
) -> ConnectorStatus:
    cfg = _get_config(db)
    client = client_from_config(cfg)
    if not client:
        raise HTTPException(status_code=400, detail="Connector is not configured")
    try:
        client.test_connection()
        cfg.last_sync_status = "ok"
        cfg.last_sync_message = "Authentication successful"
    except ConnectorError as exc:
        cfg.last_sync_status = "error"
        cfg.last_sync_message = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.commit()
    return connector_status(db, user)  # type: ignore[arg-type]


@router.post("/fetch")
def fetch_reports(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.operator)),
) -> dict:
    """Trigger a fetch of new EWA reports for all registered systems.

    Runs synchronously here for simplicity; in production this is dispatched to
    a Celery worker (see app/workers/tasks.py).
    """
    cfg = _get_config(db)
    client = client_from_config(cfg)
    if not client:
        raise HTTPException(status_code=400, detail="Connector is not configured")

    systems = db.scalars(select(System)).all()
    imported = 0
    errors: list[str] = []
    for system in systems:
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
    cfg.last_sync_message = "; ".join(errors) if errors else f"Imported {imported} report(s)"
    write_audit(db, user, "fetch_reports", "connector", "default", {"imported": imported})
    db.commit()
    return {"imported": imported, "errors": errors}
