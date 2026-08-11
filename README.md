# EWA Dashboard

A web application that consolidates **SAP EarlyWatch Alert (EWA)** reports from
multiple SAP systems into a single dashboard. Upload reports manually or pull
them automatically from SAP for Me, then track alerts, recommendations and
KPI/rating trends across your whole landscape.

> **Scope note.** This repository is a working, self-contained MVP. It fully
> implements the manual-upload + parsing pipeline, the consolidated
> alerts/recommendations dashboard, historical trend analysis and full-text
> search. The SAP for Me auto-fetch connector (OAuth 2.0) and a Celery beat
> schedule are implemented but require valid SAP credentials/entitlements to
> exchange live data. See [Limitations](#limitations).

## Features

- **Multi-system report management** – upload EWA reports (PDF / HTML / text),
  auto-extract SID, report date, chapter ratings and alerts; per-system report
  timeline; duplicate detection with explicit replace.
- **Recommendations & alerts dashboard** – consolidated cross-system view,
  filter by severity / status / chapter / system / tag, status tracking
  (open → in progress → resolved → deferred) with resolution notes.
- **Historical analysis** – alert-count and per-chapter rating trends over
  time, plus a "what changed" diff between the two latest reports.
- **Search & intelligence** – full-text search across alerts/recommendations,
  auto-tagging (HANA, Basis, Security, Performance, …) and "similar alerts"
  detection across systems.
- **SAP for Me connector** – OAuth 2.0 client-credentials flow, encrypted
  credential storage, on-demand and scheduled (weekly) auto-fetch.
- **Security** – JWT auth, role-based access (admin / operator / viewer),
  encrypted S-User/OAuth secrets at rest, audit log of changes.

## Tech stack

| Layer      | Technology |
|------------|-----------|
| Frontend   | React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Router |
| Backend    | FastAPI, SQLAlchemy 2, Pydantic v2 |
| Database   | PostgreSQL (prod) / SQLite (zero-config dev) |
| Parsing    | pdfplumber, PyMuPDF |
| Async      | Celery + Redis (optional, for scheduled fetch) |
| Auth       | OAuth2 password flow, JWT, bcrypt |

## Quick start

### Option A — Docker Compose (full stack)

```bash
docker compose up --build
# Frontend  → http://localhost:8080
# API docs  → http://localhost:8000/docs
```

The backend runs Alembic migrations on start. Seed demo data (optional):

```bash
docker compose exec backend python -m app.seed
```

### Option B — Local dev (no Docker)

**Backend** (defaults to a local SQLite file, no DB server needed):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # create demo systems + 6 weeks of reports
uvicorn app.main:app --reload
# API → http://localhost:8000  |  Swagger UI → http://localhost:8000/docs
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev                 # → http://localhost:5173 (proxies /api to :8000)
```

### Demo credentials

| Role     | Email                  | Password |
|----------|------------------------|----------|
| Admin    | `admin@example.com`    | `admin`  |
| Operator | `operator@example.com` | `operator` |
| Viewer   | `viewer@example.com`   | `viewer` |

> These seed users are for local demos only — change `FIRST_ADMIN_*` and create
> real users via `POST /api/auth/users` in any real deployment.

## Configuration

All backend settings come from environment variables (see
[`backend/.env.example`](backend/.env.example)). Key ones:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./ewa.db` | SQLAlchemy URL (use `postgresql+psycopg2://…` in prod) |
| `SECRET_KEY` | dev value | Signs JWTs **and** derives the encryption key for stored secrets — **must be changed in production** |
| `MAX_UPLOAD_MB` | `50` | Upload size limit |
| `SAPFORME_TOKEN_URL` / `SAPFORME_BASE_URL` | SAP defaults | Connector OAuth + API endpoints |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker/backend |

## Documentation

- [`docs/API.md`](docs/API.md) – endpoint reference (Swagger UI at `/docs`).
- [`docs/SAP_FOR_ME.md`](docs/SAP_FOR_ME.md) – configuring the OAuth connector.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – components and data model.

## Testing

```bash
cd backend && source .venv/bin/activate
pytest            # parser unit tests + API integration tests
```

```bash
cd frontend && npm run build   # type-check + production build
```

## Project structure

```
backend/
  app/
    api/routers/     # FastAPI routers (auth, systems, reports, alerts, trends, search, connector)
    core/            # config, database, security
    models/          # SQLAlchemy models
    schemas/         # Pydantic schemas
    services/        # pdf_parser, ingestion, trends, sapforme, sample_generator
    workers/         # Celery tasks (scheduled auto-fetch)
    main.py          # app assembly
    seed.py          # demo data seeder
  alembic/           # migrations
  tests/             # pytest suite
frontend/            # React + Vite + Tailwind SPA
docker/              # frontend Dockerfile + nginx config
docker-compose.yml
```

## Limitations

- The SAP for Me connector's OData endpoint paths (`list_reports` /
  `download_report` in `app/services/sapforme.py`) are placeholders that must be
  adjusted to your tenant's entitlement; live fetch requires a registered OAuth
  client and an authorized S-User.
- Parsing is tuned for the labelled/section-marker structure used by typical EWA
  exports (and the bundled sample generator). Heavily reformatted or
  image-only PDFs may need OCR and additional patterns.
- LLM-powered natural-language querying is noted as a future enhancement and is
  not included.
