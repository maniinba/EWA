# API Reference

Base path: `/api`. Interactive docs: `http://localhost:8000/docs` (Swagger) and
`/redoc`. All endpoints except `/auth/token`, `/health` and `/` require a
`Authorization: Bearer <token>` header.

## Roles

`viewer` < `operator` < `admin`. Endpoints note the minimum role required.

## Authentication

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/auth/token` | – | OAuth2 password flow. Form fields `username`, `password`. Returns `{access_token, token_type}`. |
| GET  | `/auth/me` | any | Current user. |
| POST | `/auth/users` | admin | Create a user `{email,password,full_name?,role}`. |
| GET  | `/auth/users` | admin | List users. |

## Systems

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET  | `/systems` | any | List systems with per-system stats (report count, open/critical alerts, latest rating). |
| POST | `/systems` | operator | Register a system `{sid,description?,system_type?,landscape?}`. |
| GET  | `/systems/{id}` | any | System detail. |
| PATCH| `/systems/{id}` | operator | Update metadata. |
| DELETE | `/systems/{id}` | admin | Delete a system and its reports. |

## Reports

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/reports/preview` | any | Parse an uploaded file and return extracted data **without** saving. |
| POST | `/reports/upload` | operator | Upload + parse + persist. Multipart `file`, optional `sid`, `report_date`, `replace_existing`. `409` if a report for the same system+date exists. |
| GET  | `/reports` | any | List reports (`?system_id=&limit=&offset=`). |
| GET  | `/reports/{id}` | any | Report detail incl. alerts and raw parsed data. |
| DELETE | `/reports/{id}` | admin | Delete a report. |

## Alerts

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET  | `/alerts` | any | Filter by `system_id, severity, status, chapter, tag`; paginated. |
| GET  | `/alerts/{id}` | any | Alert detail with system/report context. |
| GET  | `/alerts/{id}/similar` | any | Related alerts across systems (keyword + chapter overlap). |
| PATCH| `/alerts/{id}/status` | operator | Update `{status, resolution_notes?}`. |

## Trends

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET  | `/trends/{system_id}` | any | Alert-count trend + per-chapter rating history. |
| GET  | `/trends/{system_id}/what-changed` | any | Diff of the two most recent reports. |

## Search & dashboard

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET  | `/search?q=` | any | Full-text search across alert title/description/recommendation/chapter. |
| GET  | `/dashboard/summary` | any | Aggregate counts + severity/status breakdowns. |

## Connector (SAP for Me)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET  | `/connector/status` | operator | Configuration + last sync info. |
| POST | `/connector/config` | admin | Set `{client_id?,client_secret?,s_user?,s_password?,enabled}` (secrets encrypted at rest). |
| POST | `/connector/test` | operator | Validate credentials by acquiring an OAuth token. |
| POST | `/connector/fetch` | operator | Trigger a fetch for all registered systems. |

## Meta

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe. |
| GET | `/` | API banner + links. |
