"""System registration and listing endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, write_audit
from app.core.database import get_db
from app.models.models import (
    Alert,
    AlertStatus,
    RatingHistory,
    Report,
    Severity,
    System,
    User,
    UserRole,
)
from app.schemas.schemas import (
    SystemCreate,
    SystemOut,
    SystemUpdate,
    SystemWithStats,
)

router = APIRouter(prefix="/systems", tags=["systems"])


@router.post("", response_model=SystemOut, status_code=201)
def create_system(
    payload: SystemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.operator)),
) -> System:
    if db.scalar(select(System).where(System.sid == payload.sid.upper())):
        raise HTTPException(status_code=409, detail=f"System {payload.sid} already exists")
    system = System(
        sid=payload.sid.upper(),
        description=payload.description,
        system_type=payload.system_type,
        landscape=payload.landscape,
    )
    db.add(system)
    write_audit(db, user, "create_system", "system", payload.sid)
    db.commit()
    db.refresh(system)
    return system


@router.get("", response_model=list[SystemWithStats])
def list_systems(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[SystemWithStats]:
    systems = db.scalars(select(System).order_by(System.sid)).all()

    # Aggregate report counts per system.
    report_counts = dict(
        db.execute(
            select(Report.system_id, func.count(Report.id)).group_by(Report.system_id)
        ).all()
    )
    open_counts = dict(
        db.execute(
            select(Alert.system_id, func.count(Alert.id))
            .where(Alert.status != AlertStatus.resolved)
            .group_by(Alert.system_id)
        ).all()
    )
    critical_counts = dict(
        db.execute(
            select(Alert.system_id, func.count(Alert.id))
            .where(Alert.severity == Severity.red, Alert.status != AlertStatus.resolved)
            .group_by(Alert.system_id)
        ).all()
    )

    out: list[SystemWithStats] = []
    for s in systems:
        latest_report = db.scalar(
            select(Report)
            .where(Report.system_id == s.id)
            .order_by(Report.report_date.desc())
            .limit(1)
        )
        item = SystemWithStats.model_validate(s)
        item.report_count = report_counts.get(s.id, 0)
        item.open_alerts = open_counts.get(s.id, 0)
        item.critical_alerts = critical_counts.get(s.id, 0)
        item.latest_rating = latest_report.overall_rating if latest_report else None
        out.append(item)
    return out


@router.get("/{system_id}", response_model=SystemOut)
def get_system(
    system_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> System:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return system


@router.patch("/{system_id}", response_model=SystemOut)
def update_system(
    system_id: uuid.UUID,
    payload: SystemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.operator)),
) -> System:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(system, field_name, value)
    write_audit(db, user, "update_system", "system", str(system_id))
    db.commit()
    db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=204)
def delete_system(
    system_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin)),
):
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    db.delete(system)
    write_audit(db, user, "delete_system", "system", str(system_id))
    db.commit()
