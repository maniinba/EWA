"""Shared FastAPI dependencies: auth, role checks, audit logging."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import AuditLog, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/token")

_ROLE_ORDER = {UserRole.viewer: 0, UserRole.operator: 1, UserRole.admin: 2}


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exc
    user = db.scalar(select(User).where(User.email == payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_exc
    return user


def require_role(minimum: UserRole):
    """Dependency factory enforcing a minimum role level."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if _ROLE_ORDER[user.role] < _ROLE_ORDER[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} role or higher",
            )
        return user

    return checker


def write_audit(
    db: Session,
    user: User | None,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_email=user.email if user else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id else None,
            detail=detail,
        )
    )
