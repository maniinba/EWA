"""Trend and comparison endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import System, User
from app.schemas.schemas import TrendResponse, WhatChanged
from app.services.trends import build_trends, what_changed

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/{system_id}", response_model=TrendResponse)
def system_trends(
    system_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TrendResponse:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return build_trends(db, system)


@router.get("/{system_id}/what-changed", response_model=WhatChanged)
def system_what_changed(
    system_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WhatChanged:
    system = db.get(System, system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return what_changed(db, system)
