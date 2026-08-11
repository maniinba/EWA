"""Seed the database with demo systems and several weeks of EWA reports.

Run with:  python -m app.seed
"""
from __future__ import annotations

from datetime import date, timedelta

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.models import User, UserRole
from app.services.ingestion import persist_report
from app.services.pdf_parser import parse_ewa_text
from app.services.sample_generator import ALERT_CATALOGUE, build_report_text

DEMO_SYSTEMS = [
    ("PRD", "ABAP", "PROD", "S/4HANA Production"),
    ("QAS", "ABAP", "QA", "S/4HANA Quality Assurance"),
    ("BWP", "HANA", "PROD", "BW/4HANA Production"),
]


def _weekly_alerts(week_index: int, base: list[tuple]) -> list[tuple]:
    """Vary alerts week over week so trends and 'what changed' are meaningful.

    Each subsequent week resolves one more finding (simulating remediation), so
    the alert trend declines steadily and consecutive reports differ.
    """
    # Remediation order: address the most severe / oldest findings first.
    resolve_order = [
        "default passwords",   # week 1
        "kernel",              # week 2
        "update errors",       # week 3
        "delta merge",         # week 4
        "database growth",     # week 5
    ]
    to_drop = set(resolve_order[:week_index])
    return [a for a in base if not any(k in a[2].lower() for k in to_drop)]


def _weekly_ratings(week_index: int) -> list[tuple]:
    """Ratings improve as findings are remediated."""
    from app.services.sample_generator import RATINGS

    ratings = dict(RATINGS)
    if week_index >= 2:
        ratings["Security"] = "YELLOW"
    if week_index >= 4:
        ratings["Security"] = "GREEN"
    if week_index >= 3:
        ratings["Performance"] = "YELLOW"
    if week_index >= 5:
        ratings["Database Performance"] = "GREEN"
    return list(ratings.items())


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Users
        for email, pw, role in [
            ("admin@example.com", "admin", UserRole.admin),
            ("operator@example.com", "operator", UserRole.operator),
            ("viewer@example.com", "viewer", UserRole.viewer),
        ]:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, hashed_password=hash_password(pw), role=role,
                            full_name=role.value.title()))
        db.commit()

        today = date.today()
        weeks = 6
        total = 0
        for sid, stype, landscape, desc in DEMO_SYSTEMS:
            for w in range(weeks):
                report_date = today - timedelta(weeks=(weeks - 1 - w))
                alerts = _weekly_alerts(w, ALERT_CATALOGUE)
                ratings = _weekly_ratings(w)
                text = build_report_text(sid, report_date, alerts, ratings)
                # Ensure system_type reflected in text for parser
                text = text.replace("System Type: ABAP", f"System Type: {stype}")
                parsed = parse_ewa_text(text)
                try:
                    report = persist_report(
                        db, parsed, file_name=f"{sid}_{report_date}.pdf",
                        override_sid=sid, override_date=report_date,
                        allow_replace=True,
                    )
                    # Enrich system metadata.
                    report.system.description = desc
                    report.system.landscape = landscape
                    report.system.system_type = stype
                    total += 1
                except ValueError as exc:  # pragma: no cover
                    print(f"Skipped {sid} {report_date}: {exc}")
            db.commit()
        print(f"Seeded {len(DEMO_SYSTEMS)} systems and {total} reports.")


if __name__ == "__main__":
    seed()
