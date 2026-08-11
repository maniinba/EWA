"""Administrative maintenance endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role, write_audit
from app.core.database import get_db
from app.models.models import (
    Alert,
    RatingHistory,
    Report,
    System,
    User,
    UserRole,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/purge")
def purge_data(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
) -> dict:
    """Delete ALL systems, reports, alerts and rating history.

    Users, connector configuration and the audit log are preserved. Intended
    for clearing demo/seed data before loading real reports.
    """
    counts = {
        "alerts": db.scalar(select(func.count(Alert.id))) or 0,
        "ratings": db.scalar(select(func.count(RatingHistory.id))) or 0,
        "reports": db.scalar(select(func.count(Report.id))) or 0,
        "systems": db.scalar(select(func.count(System.id))) or 0,
    }
    # Order respects FK dependencies (children first).
    db.execute(delete(Alert))
    db.execute(delete(RatingHistory))
    db.execute(delete(Report))
    db.execute(delete(System))
    write_audit(db, user, "purge_data", "system", None, counts)
    db.commit()
    return {"deleted": counts}
