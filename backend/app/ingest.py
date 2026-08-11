"""Bulk-ingest EWA report files from the command line.

Usage:
    python -m app.ingest <file-or-glob> [<file-or-glob> ...] [--replace]

Examples:
    python -m app.ingest "C:/Users/me/Downloads/*_EWA.DOC"
    python -m app.ingest ./reports/VSP_*.DOC --replace

Parses each SAP EarlyWatch Alert document (WordML .DOC / PDF / HTML) and stores
it. SID / report date / overall rating are taken from the filename when the
document itself does not supply them. Existing reports for the same system+date
are skipped unless --replace is given.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

# Windows consoles default to cp1252; force UTF-8 so report text prints safely.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except (AttributeError, ValueError):  # pragma: no cover
    pass

from app.core.database import Base, SessionLocal, engine
from app.models.models import UploadMethod
from app.services.ingestion import DuplicateReportError, persist_report
from app.services.pdf_parser import parse_ewa_document


def _expand(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pat in patterns:
        matched = glob.glob(pat)
        if matched:
            files.extend(Path(m) for m in matched)
        elif Path(pat).exists():
            files.append(Path(pat))
        else:
            print(f"  ! no match for: {pat}")
    # De-duplicate, keep order.
    seen: set[str] = set()
    out: list[Path] = []
    for f in files:
        key = str(f.resolve())
        if key not in seen and f.is_file():
            seen.add(key)
            out.append(f)
    return out


def ingest_paths(patterns: list[str], replace: bool = False) -> dict:
    Base.metadata.create_all(bind=engine)
    files = _expand(patterns)
    if not files:
        print("No files matched.")
        return {"imported": 0, "skipped": 0, "failed": 0}

    imported = skipped = failed = 0
    with SessionLocal() as db:
        for path in files:
            try:
                data = path.read_bytes()
                parsed = parse_ewa_document(data, path.name)
                report = persist_report(
                    db,
                    parsed,
                    file_name=path.name,
                    file_size=len(data),
                    upload_method=UploadMethod.manual,
                    allow_replace=replace,
                )
                db.commit()
                imported += 1
                rating = report.overall_rating.value if report.overall_rating else "-"
                print(
                    f"  [ok]   {path.name}  ->  {report.system.sid} {report.report_date}  "
                    f"({len(report.alerts)} alerts, rating {rating})"
                )
            except DuplicateReportError as exc:
                db.rollback()
                skipped += 1
                print(f"  [skip] {path.name}  ->  {exc}")
            except Exception as exc:  # noqa: BLE001 - surface any parse/IO error per file
                db.rollback()
                failed += 1
                print(f"  [FAIL] {path.name}  ->  {type(exc).__name__}: {exc}")
    print(f"\nImported {imported}, skipped {skipped}, failed {failed}.")
    return {"imported": imported, "skipped": skipped, "failed": failed}


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--replace"]
    replace = "--replace" in argv
    if not args:
        print(__doc__)
        return 1
    ingest_paths(args, replace=replace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
