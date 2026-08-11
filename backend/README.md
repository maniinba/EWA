# EWA Dashboard — Backend

FastAPI service for parsing, storing and analyzing SAP EarlyWatch Alert reports.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional; defaults work out of the box (SQLite)
python -m app.seed              # demo systems + 6 weeks of reports
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Migrations (Alembic)

The app calls `create_all` on startup for dev convenience; use Alembic for
production schema management.

```bash
alembic upgrade head                       # apply migrations
alembic revision --autogenerate -m "msg"   # create a new migration
```

## Tests

```bash
pytest            # parser unit tests + API integration tests
```

## Layout

```
app/
  api/routers/   auth, systems, reports, alerts, trends, search, connector
  core/          config, database (portable UUID/JSON types), security
  models/        SQLAlchemy models + enums
  schemas/       Pydantic request/response models
  services/      pdf_parser, ingestion, trends, sapforme, sample_generator
  workers/       Celery app + scheduled auto-fetch
  main.py        FastAPI app assembly, startup seeding
  seed.py        demo data seeder
```

See [`../docs/`](../docs) for the API reference, architecture and connector
setup.
