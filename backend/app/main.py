"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.models import User, UserRole
from app.api.routers import (
    alerts,
    auth,
    connector,
    reports,
    search,
    systems,
    trends,
)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_admin() -> None:
    """Create the seed admin user on first startup (dev convenience)."""
    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.email == settings.first_admin_email))
        if not exists:
            db.add(
                User(
                    email=settings.first_admin_email,
                    hashed_password=hash_password(settings.first_admin_password),
                    full_name="Administrator",
                    role=UserRole.admin,
                )
            )
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    seed_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Consolidated SAP EarlyWatch Alert recommendations & analysis dashboard.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_prefix = settings.api_prefix
app.include_router(auth.router, prefix=_prefix)
app.include_router(systems.router, prefix=_prefix)
app.include_router(reports.router, prefix=_prefix)
app.include_router(alerts.router, prefix=_prefix)
app.include_router(trends.router, prefix=_prefix)
app.include_router(search.router, prefix=_prefix)
app.include_router(connector.router, prefix=_prefix)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"message": f"{settings.app_name} API", "docs": "/docs", "health": "/health"}
