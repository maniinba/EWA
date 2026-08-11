# Architecture

## Overview

```
        ┌──────────────┐        REST/JSON (JWT)        ┌───────────────────┐
        │  React SPA   │  ───────────────────────────▶ │   FastAPI backend │
        │ (Vite/TW)    │ ◀───────────────────────────  │                   │
        └──────────────┘                                │  ┌─────────────┐  │
                                                        │  │  services   │  │
   ┌──────────────┐   auto-fetch (OAuth2)               │  │ parser/     │  │
   │  SAP for Me  │ ◀────────────────────────────────── │  │ ingestion/  │  │
   │   API        │                                     │  │ trends/     │  │
   └──────────────┘                                     │  │ sapforme    │  │
                                                        │  └─────────────┘  │
                          ┌──────────┐   ┌──────────┐   └─────────┬─────────┘
                          │  Redis   │◀─▶│  Celery  │             │ SQLAlchemy
                          └──────────┘   │  worker  │             ▼
                                         └──────────┘   ┌───────────────────┐
                                                        │ PostgreSQL/SQLite │
                                                        └───────────────────┘
```

## Backend layers

- **`api/routers`** – thin HTTP layer: request validation, auth/role checks,
  audit logging, delegation to services. No business logic beyond wiring.
- **`services`** – the domain logic:
  - `pdf_parser` – document → structured `ParsedReport` (metadata, ratings,
    alerts, SAP notes, tags). Pure functions, unit-tested without a DB.
  - `ingestion` – persist a `ParsedReport` into normalized tables; shared by
    manual upload and auto-fetch so both produce identical records.
  - `trends` – aggregate reports/ratings into trend series and diffs.
  - `sapforme` – OAuth client + report retrieval; the only module that talks to
    SAP, so the rest of the app is testable offline.
- **`models`** – SQLAlchemy ORM. Portable `GUID` and `PortableJSON` column types
  map to native PostgreSQL `UUID`/`JSONB` and degrade to `CHAR(36)`/`JSON` on
  SQLite, so the same schema runs in dev and prod.
- **`core`** – settings (`pydantic-settings`), DB engine/session, security
  (JWT, bcrypt, Fernet secret encryption).
- **`workers`** – Celery app + the weekly `fetch_all_reports` beat task.

## Data model

```
systems 1───∞ reports 1───∞ alerts
   │                  │
   │                  └──∞ ratings_history (per chapter, per report_date)
   └──∞ ratings_history

connector_config   (singleton, encrypted secrets)
users              (auth + RBAC)
audit_log          (who changed what)
```

- `reports` is unique on `(system_id, report_date)` — one EWA per system per
  week; re-upload requires `replace_existing`.
- `alerts` denormalizes `system_id` for fast cross-system filtering.
- `ratings_history` is the source for per-chapter trend lines and the
  "what changed" rating diff.
- `parsed_data` (JSON/JSONB) on `reports` keeps the full parser output for
  re-processing without the original file.

## Request lifecycle (upload)

1. `POST /reports/upload` receives the file → size/type validation.
2. `pdf_parser.parse_ewa_document` extracts text (pdfplumber) and structures it.
3. The raw file is written to `UPLOAD_DIR`; the DB record is the source of truth.
4. `ingestion.persist_report` upserts the system, report, alerts and rating
   history in one transaction (duplicate → `409`).
5. An audit-log entry is written; the report detail is returned.

## Security

- JWT bearer tokens (HS256) signed with `SECRET_KEY`.
- Role gate via a `require_role(minimum)` dependency factory.
- Connector secrets encrypted with Fernet using a key derived from
  `SECRET_KEY` (`core.security.encrypt_secret`).
- All mutations recorded in `audit_log`.
