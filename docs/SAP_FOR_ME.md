# SAP for Me Connector Setup

The connector pulls EWA reports directly from SAP for Me using the OAuth 2.0
**client-credentials** flow. Live data exchange requires an SAP for Me
entitlement, a registered OAuth client and an authorized S-User.

## 1. Prerequisites

- An S-User with authorization to view/download EarlyWatch Alert reports for the
  target systems in SAP for Me.
- An OAuth 2.0 client (client id + secret) registered for API access under your
  SAP for Me / SAP Universal ID account.

## 2. Configure the connector

As an **admin**, call `POST /api/connector/config` (or use the Connector page in
the UI):

```json
{
  "client_id": "sb-xxxx",
  "client_secret": "••••••",
  "s_user": "S0001234567",
  "s_password": "••••••",
  "enabled": true
}
```

Secrets are encrypted at rest with a key derived from `SECRET_KEY` (Fernet /
AES). They are never returned by the API.

## 3. Test & fetch

- `POST /api/connector/test` – validates the credentials by acquiring an OAuth
  token from `SAPFORME_TOKEN_URL`.
- `POST /api/connector/fetch` – lists and downloads available reports for every
  registered system, parses and stores them (`upload_method = auto_fetch`).

## 4. Scheduled auto-fetch

With Redis + the Celery worker running (see `docker-compose.yml`), the beat
schedule in `app/workers/tasks.py` runs `fetch_all_reports` every **Monday at
06:00 UTC**. Adjust the `crontab(...)` entry to change the cadence.

## 5. Adapting the endpoints

The concrete OData paths differ per tenant/entitlement. Update these methods in
[`backend/app/services/sapforme.py`](../backend/app/services/sapforme.py) to
match your API contract:

- `SAPForMeClient.list_reports(sid)` – list report metadata for a system.
- `SAPForMeClient.download_report(ref)` – download a report document by id.

The token exchange (`_fetch_token`) follows the standard client-credentials
grant and generally needs no changes.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `OAuth token request failed` on test | Wrong client id/secret or token URL; check `SAPFORME_TOKEN_URL`. |
| Token OK but `Failed to list reports` | OData path/entitlement mismatch — adapt `list_reports`. |
| Reports fetched but empty of alerts | Report format differs from the parser's expectations; extend patterns in `app/services/pdf_parser.py`. |
