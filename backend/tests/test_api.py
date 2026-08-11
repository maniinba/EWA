"""Integration tests for the API endpoints."""
from __future__ import annotations

import io
from datetime import date

from app.services.sample_generator import build_report_pdf


def _upload(client, auth, sid, report_date, replace=False):
    pdf = build_report_pdf(sid, report_date)
    files = {"file": (f"{sid}.pdf", io.BytesIO(pdf), "application/pdf")}
    data = {"replace_existing": str(replace).lower()}
    return client.post("/api/reports/upload", headers=auth, files=files, data=data)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_auth_required(client):
    assert client.get("/api/systems").status_code == 401


def test_login_bad_password(client):
    r = client.post("/api/auth/token", data={"username": "admin@example.com", "password": "x"})
    assert r.status_code == 401


def test_upload_and_list_flow(client, auth):
    r = _upload(client, auth, "T01", date(2026, 3, 1))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["system_sid"] == "T01"
    assert len(body["alerts"]) >= 5

    systems = client.get("/api/systems", headers=auth).json()
    assert any(s["sid"] == "T01" for s in systems)

    alerts = client.get("/api/alerts", headers=auth, params={"system_id": body["system_id"]}).json()
    assert len(alerts) >= 5


def test_duplicate_report_conflict_then_replace(client, auth):
    _upload(client, auth, "T02", date(2026, 3, 1))
    dup = _upload(client, auth, "T02", date(2026, 3, 1))
    assert dup.status_code == 409
    replaced = _upload(client, auth, "T02", date(2026, 3, 1), replace=True)
    assert replaced.status_code == 201


def test_preview_does_not_persist(client, auth):
    pdf = build_report_pdf("T99", date(2026, 4, 1))
    files = {"file": ("T99.pdf", io.BytesIO(pdf), "application/pdf")}
    prev = client.post("/api/reports/preview", headers=auth, files=files).json()
    assert prev["sid"] == "T99"
    assert prev["alert_count"] >= 5
    systems = client.get("/api/systems", headers=auth).json()
    assert not any(s["sid"] == "T99" for s in systems)


def test_alert_status_update(client, auth):
    r = _upload(client, auth, "T03", date(2026, 3, 8))
    alerts = client.get("/api/alerts", headers=auth,
                        params={"system_id": r.json()["system_id"]}).json()
    aid = alerts[0]["id"]
    upd = client.patch(f"/api/alerts/{aid}/status", headers=auth,
                       json={"status": "resolved", "resolution_notes": "done"})
    assert upd.status_code == 200
    assert upd.json()["status"] == "resolved"
    assert upd.json()["resolved_at"] is not None


def test_trends_and_what_changed(client, auth):
    _upload(client, auth, "T04", date(2026, 3, 1))
    r2 = _upload(client, auth, "T04", date(2026, 3, 8))
    sysid = r2.json()["system_id"]
    trends = client.get(f"/api/trends/{sysid}", headers=auth).json()
    assert len(trends["alert_trend"]) == 2
    wc = client.get(f"/api/trends/{sysid}/what-changed", headers=auth).json()
    assert wc["from_date"] is not None and wc["to_date"] is not None


def test_search(client, auth):
    _upload(client, auth, "T05", date(2026, 3, 1))
    res = client.get("/api/search", headers=auth, params={"q": "kernel"}).json()
    assert res["total"] >= 1


def test_dashboard_summary(client, auth):
    summary = client.get("/api/dashboard/summary", headers=auth).json()
    assert summary["total_systems"] >= 1
    assert set(summary["severity_breakdown"]) == {"red", "yellow", "green", "gray"}


def test_rbac_viewer_cannot_upload(client, auth):
    # Create a viewer user, then confirm it cannot upload.
    client.post("/api/auth/users", headers=auth,
                json={"email": "v@example.com", "password": "viewer", "role": "viewer"})
    tok = client.post("/api/auth/token",
                      data={"username": "v@example.com", "password": "viewer"}).json()["access_token"]
    vauth = {"Authorization": f"Bearer {tok}"}
    r = _upload(client, vauth, "T06", date(2026, 3, 1))
    assert r.status_code == 403


def test_connector_status_unconfigured(client, auth):
    st = client.get("/api/connector/status", headers=auth).json()
    assert st["configured"] is False
