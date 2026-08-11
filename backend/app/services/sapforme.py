"""SAP for Me connector.

Implements the OAuth 2.0 client-credentials flow against the SAP accounts
token endpoint and a thin client for pulling EWA reports for registered
systems. Network calls are isolated here so the rest of the app can be run
and tested without SAP connectivity.

NOTE: SAP for Me / SAP for Me API access requires a valid S-User with the
appropriate authorizations and an OAuth client registered in SAP for Me.
Endpoint paths differ by tenant; ``fetch_reports`` is written defensively and
returns an empty list when the connector is not fully configured.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core.config import settings


class ConnectorError(RuntimeError):
    pass


@dataclass
class _CachedToken:
    value: str
    expires_at: float


class SAPForMeClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str | None = None,
        token_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = (base_url or settings.sapforme_base_url).rstrip("/")
        self.token_url = token_url or settings.sapforme_token_url
        self.timeout = timeout
        self._token: _CachedToken | None = None

    # ------------------------------------------------------------------ #
    # OAuth
    # ------------------------------------------------------------------ #
    def _fetch_token(self) -> _CachedToken:
        try:
            resp = httpx.post(
                self.token_url,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network path
            raise ConnectorError(f"OAuth token request failed: {exc}") from exc

        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise ConnectorError("OAuth response did not contain an access_token")
        expires_in = int(payload.get("expires_in", 3600))
        # Refresh 60s before expiry.
        return _CachedToken(value=access_token, expires_at=time.time() + expires_in - 60)

    def get_token(self) -> str:
        if self._token is None or self._token.expires_at <= time.time():
            self._token = self._fetch_token()
        return self._token.value

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_token()}", "Accept": "application/json"}

    # ------------------------------------------------------------------ #
    # Report retrieval
    # ------------------------------------------------------------------ #
    def test_connection(self) -> bool:
        """Validate credentials by acquiring a token."""
        self.get_token()
        return True

    def list_reports(self, sid: str) -> list[dict]:
        """List available EWA reports for a system (metadata only).

        The concrete SAP for Me endpoint depends on the tenant configuration.
        Adjust the path below to match your entitlement.
        """
        url = f"{self.base_url}/services/odata/v1/EWAReports"
        try:
            resp = httpx.get(
                url,
                params={"$filter": f"systemId eq '{sid}'"},
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network path
            raise ConnectorError(f"Failed to list reports for {sid}: {exc}") from exc
        data = resp.json()
        return data.get("value", data if isinstance(data, list) else [])

    def download_report(self, report_ref: str) -> bytes:
        """Download a single EWA report document by reference/id."""
        url = f"{self.base_url}/services/odata/v1/EWAReports('{report_ref}')/$value"
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network path
            raise ConnectorError(f"Failed to download report {report_ref}: {exc}") from exc
        return resp.content


def client_from_config(config) -> SAPForMeClient | None:
    """Build a client from a ConnectorConfig row, decrypting the secret."""
    from app.core.security import decrypt_secret

    if not config or not config.client_id or not config.client_secret_enc:
        return None
    return SAPForMeClient(
        client_id=config.client_id,
        client_secret=decrypt_secret(config.client_secret_enc),
    )
