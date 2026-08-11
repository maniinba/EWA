"""Unit tests for the EWA PDF/text parser."""
from __future__ import annotations

from datetime import date

from app.services.pdf_parser import parse_ewa_document, parse_ewa_text
from app.services.sample_generator import build_report_pdf, build_report_text


def test_parse_text_extracts_metadata():
    text = build_report_text("PRD", date(2026, 1, 15))
    parsed = parse_ewa_text(text)
    assert parsed.sid == "PRD"
    assert parsed.report_date == date(2026, 1, 15)
    assert parsed.system_type == "ABAP"
    assert parsed.overall_rating == "red"


def test_parse_text_extracts_ratings_without_overall():
    parsed = parse_ewa_text(build_report_text("PRD", date(2026, 1, 15)))
    chapters = {r.chapter.lower() for r in parsed.ratings}
    assert "security" in chapters
    assert "performance" in chapters
    # 'Overall Assessment' must not leak into chapter ratings.
    assert not any(c.startswith("overall") for c in chapters)


def test_parse_text_extracts_alerts_and_notes():
    parsed = parse_ewa_text(build_report_text("PRD", date(2026, 1, 15)))
    assert len(parsed.alerts) >= 5
    kernel = next(a for a in parsed.alerts if "kernel" in a.title.lower())
    assert kernel.severity == "red"
    assert "2083594" in kernel.sap_note_refs
    assert "Security" in kernel.tags


def test_parse_pdf_roundtrip():
    pdf = build_report_pdf("BWP", date(2025, 12, 1))
    assert pdf[:5] == b"%PDF-"
    parsed = parse_ewa_document(pdf, "BWP.pdf")
    assert parsed.sid == "BWP"
    assert parsed.report_date == date(2025, 12, 1)
    assert len(parsed.alerts) >= 5


def test_parse_missing_fields_is_graceful():
    parsed = parse_ewa_text("Some unrelated document with no EWA structure.")
    assert parsed.sid is None
    assert parsed.report_date is None
    assert parsed.alerts == []


def test_html_extraction():
    html = "<html><body>System ID: DEV<br>Report Date: 01.02.2026</body></html>"
    parsed = parse_ewa_document(html.encode(), "report.html")
    assert parsed.sid == "DEV"
    assert parsed.report_date == date(2026, 2, 1)
