"""Generate synthetic EWA report PDFs for demos and tests.

The generated text follows the same conventions the parser recognises
(labelled metadata, a chapter/rating assessment table and ``ALERT [SEV]``
blocks), so a generated PDF round-trips cleanly through the parser.
"""
from __future__ import annotations

import io
from datetime import date

# Deterministic catalogue of realistic-sounding EWA findings.
ALERT_CATALOGUE = [
    ("RED", "Performance", "Long running dialog steps degrade end-user response time",
     "Average dialog response time exceeded 1200 ms during peak hours.",
     "Review expensive SQL statements and add appropriate indexes. See SAP Note 1257308.",
     ),
    ("RED", "Security", "SAP kernel is not on a current patch level",
     "The installed kernel patch level is below the recommended minimum and exposes known issues.",
     "Update the kernel to the latest patch level. See SAP Note 2083594.",
     ),
    ("YELLOW", "Database", "Database growth trend requires attention",
     "The database has grown by 18% over the last 4 weeks.",
     "Enable data archiving for large tables. See SAP Note 2388483.",
     ),
    ("YELLOW", "HANA", "Delta merge not optimally configured",
     "Several column store tables show a high delta storage ratio.",
     "Review auto-merge parameters. See SAP Note 2057046.",
     ),
    ("GREEN", "Hardware", "CPU and memory utilization within healthy range",
     "Peak CPU utilization stayed below 65% during the analysis period.",
     "No action required.",
     ),
    ("YELLOW", "Basis", "Number of update errors above threshold",
     "42 update errors (SM13) were recorded during the analysis week.",
     "Investigate failed update records. See SAP Note 385830.",
     ),
    ("GREEN", "Fiori", "Fiori launchpad services are stable",
     "No gateway service errors were detected.",
     "No action required.",
     ),
    ("RED", "Security", "Default passwords still active for standard users",
     "Standard users SAP* and DDIC use default passwords in at least one client.",
     "Change default passwords immediately. See SAP Note 2467.",
     ),
]

RATINGS = [
    ("Hardware Capacity", "GREEN"),
    ("Performance", "RED"),
    ("SAP System Operating", "YELLOW"),
    ("Database Performance", "YELLOW"),
    ("Security", "RED"),
    ("Software Configuration", "GREEN"),
]


def _overall(ratings: list[tuple]) -> str:
    order = {"RED": 3, "YELLOW": 2, "GREEN": 1, "GRAY": 0}
    return max((r for _, r in ratings), key=lambda r: order.get(r.upper(), 0))


def build_report_text(
    sid: str,
    report_date: date,
    alerts: list[tuple] | None = None,
    ratings: list[tuple] | None = None,
) -> str:
    """Build the plain-text body of an EWA report."""
    alerts = alerts if alerts is not None else ALERT_CATALOGUE
    ratings = ratings if ratings is not None else RATINGS
    lines = [
        "SAP EarlyWatch Alert Report",
        "=" * 60,
        f"System ID: {sid}",
        "System Type: ABAP",
        f"Report Date: {report_date.strftime('%d.%m.%Y')}",
        f"Overall Assessment: {_overall(ratings)}",
        "",
        "1. Service Summary - Rating Overview",
        "-" * 60,
    ]
    for chapter, rating in ratings:
        dots = "." * max(4, 45 - len(chapter))
        lines.append(f"{chapter} {dots} {rating}")
    lines += ["", "2. Alerts and Recommendations", "-" * 60, ""]
    for sev, chapter, title, desc, rec in alerts:
        lines.append(f"ALERT [{sev}] {chapter}: {title}")
        lines.append(f"Description: {desc}")
        lines.append(f"Recommendation: {rec}")
        lines.append("")
    return "\n".join(lines)


def build_report_pdf(
    sid: str,
    report_date: date,
    alerts: list[tuple] | None = None,
    ratings: list[tuple] | None = None,
) -> bytes:
    """Render the report text into a simple multi-line PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    text = build_report_text(sid, report_date, alerts, ratings)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica", 9)
    x, y = 40, height - 40
    for line in text.splitlines():
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 40
        c.drawString(x, y, line[:120])
        y -= 12
    c.showPage()
    c.save()
    return buffer.getvalue()
