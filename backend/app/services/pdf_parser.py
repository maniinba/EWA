"""EWA report parsing service.

Extracts structured data (system metadata, chapter ratings, alerts and SAP
Note references) from SAP EarlyWatch Alert reports. PDF text is read with
``pdfplumber``; the same extraction logic is reused for plain-text / HTML
sources so the parser can be unit-tested without a PDF.

Real EWA reports vary between releases, so the parser is deliberately
tolerant: it works from labelled fields and section markers and degrades
gracefully (returning ``None`` fields) rather than raising when a pattern is
missing.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime

# --------------------------------------------------------------------------- #
# Keyword → tag mapping for auto-categorisation
# --------------------------------------------------------------------------- #
TAG_KEYWORDS: dict[str, list[str]] = {
    "HANA": ["hana", "column store", "delta merge", "in-memory"],
    "Basis": ["abap", "basis", "work process", "dispatcher", "kernel", "rfc"],
    "Security": ["security", "password", "authorization", "authorisation",
                 "vulnerab", "patch", "encryption", "gateway"],
    "Performance": ["performance", "response time", "dialog", "throughput",
                    "load", "cpu", "memory"],
    "Database": ["database", "tablespace", "backup", "index", "db02", "growth"],
    "Fiori": ["fiori", "ui5", "launchpad", "gateway service"],
    "Hardware": ["hardware", "cpu utilization", "paging", "disk"],
}

SEVERITY_WORDS = {
    "red": "red",
    "critical": "red",
    "high": "red",
    "very high": "red",
    "yellow": "yellow",
    "medium": "yellow",
    "warning": "yellow",
    "green": "green",
    "low": "green",
    "ok": "green",
    "gray": "gray",
    "grey": "gray",
    "info": "gray",
}

_SAP_NOTE_RE = re.compile(r"(?:SAP\s*Note[s]?\s*[:#]?\s*)(\d{6,8})", re.IGNORECASE)
_NOTE_NUM_RE = re.compile(r"\b(\d{7})\b")


@dataclass
class ParsedRating:
    chapter: str
    rating: str
    score: int = 0


@dataclass
class ParsedAlert:
    title: str
    severity: str = "yellow"
    chapter: str | None = None
    description: str | None = None
    recommendation: str | None = None
    sap_note_refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ParsedReport:
    sid: str | None = None
    report_date: date | None = None
    system_type: str | None = None
    overall_rating: str | None = None
    ratings: list[ParsedRating] = field(default_factory=list)
    alerts: list[ParsedAlert] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "sid": self.sid,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "system_type": self.system_type,
            "overall_rating": self.overall_rating,
            "ratings": [r.__dict__ for r in self.ratings],
            "alerts": [a.__dict__ for a in self.alerts],
            "alert_count": len(self.alerts),
        }


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF byte stream using pdfplumber."""
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parts.append(text)
    return "\n".join(parts)


def extract_text(data: bytes, filename: str = "") -> str:
    """Extract text from supported document types."""
    name = filename.lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        return extract_text_from_pdf(data)
    if name.endswith((".html", ".htm")):
        return _strip_html(data.decode("utf-8", errors="ignore"))
    # Plain text / .txt / unknown → best-effort decode.
    return data.decode("utf-8", errors="ignore")


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    return re.sub(r"[ \t]+", " ", text)


# --------------------------------------------------------------------------- #
# Field helpers
# --------------------------------------------------------------------------- #
def _normalise_severity(word: str) -> str:
    return SEVERITY_WORDS.get(word.strip().lower(), "yellow")


def _severity_score(sev: str) -> int:
    return {"red": 3, "yellow": 2, "green": 1, "gray": 0}.get(sev, 0)


def _auto_tags(text: str) -> list[str]:
    low = text.lower()
    tags = [tag for tag, kws in TAG_KEYWORDS.items() if any(k in low for k in kws)]
    return tags


def _extract_notes(text: str) -> list[str]:
    notes = set(_SAP_NOTE_RE.findall(text))
    # Fall back to bare 7-digit numbers only when "note" appears nearby.
    if "note" in text.lower():
        notes.update(_NOTE_NUM_RE.findall(text))
    return sorted(notes)


def _parse_date(value: str) -> date | None:
    value = value.strip()
    fmts = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"]
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Core parsing
# --------------------------------------------------------------------------- #
def _parse_metadata(text: str, result: ParsedReport) -> None:
    sid_match = re.search(
        r"(?:System\s*ID|SID|Installed\s*System)\s*[:\-]?\s*([A-Z0-9]{3})\b", text
    )
    if sid_match:
        result.sid = sid_match.group(1).upper()

    for pat in (
        r"Report\s*Date\s*[:\-]?\s*([0-9]{1,2}[.\-/][0-9]{1,2}[.\-/][0-9]{2,4})",
        r"Analysis\s*(?:from|of)\s*[:\-]?\s*([0-9]{1,2}[.\-/][0-9]{1,2}[.\-/][0-9]{2,4})",
        r"Date\s*[:\-]?\s*([0-9]{1,2}[.\-/][0-9]{1,2}[.\-/][0-9]{4})",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m and (d := _parse_date(m.group(1))):
            result.report_date = d
            break

    type_match = re.search(
        r"System\s*Type\s*[:\-]?\s*(ABAP|HANA|Java|JAVA|Dual[- ]Stack)", text, re.IGNORECASE
    )
    if type_match:
        result.system_type = type_match.group(1).upper().replace("JAVA", "Java")

    overall = re.search(
        r"Overall\s*(?:Assessment|Rating)\s*[:\-]?\s*(RED|YELLOW|GREEN|Critical|Warning|OK|"
        r"red|yellow|green)", text, re.IGNORECASE
    )
    if overall:
        result.overall_rating = _normalise_severity(overall.group(1))


def _parse_ratings(text: str, result: ParsedReport) -> None:
    """Parse a 'chapter — rating' assessment table.

    Recognised line shapes (case-insensitive on the colour):
        Performance ................ RED
        Security                     YELLOW
        Hardware Capacity   |  GREEN
    """
    seen: set[str] = set()
    line_re = re.compile(
        r"^\s*([A-Za-z][A-Za-z0-9 &/()\-]{2,60}?)\s*[.:|\t ]{2,}\s*"
        r"(RED|YELLOW|GREEN|GRAY|GREY|Critical|Warning|OK|Good)\s*$",
        re.IGNORECASE,
    )
    for raw in text.splitlines():
        m = line_re.match(raw)
        if not m:
            continue
        chapter = re.sub(r"\s+", " ", m.group(1)).strip(" .:-|")
        rating = _normalise_severity(m.group(2))
        key = chapter.lower()
        # 'Overall Assessment' is captured separately as the report rating.
        if len(chapter) < 3 or key in seen or key.startswith("overall"):
            continue
        seen.add(key)
        result.ratings.append(ParsedRating(chapter=chapter, rating=rating, score=_severity_score(rating)))


def _parse_alerts(text: str, result: ParsedReport) -> None:
    """Parse alert blocks.

    Blocks are delimited by an ``ALERT`` marker line:
        ALERT [RED] Performance: Long running dialog steps
        Description: ...
        Recommendation: ...
        SAP Note 123456
    Blocks end at the next ALERT marker or a blank-line boundary.
    """
    block_re = re.compile(
        r"ALERT\s*\[(RED|YELLOW|GREEN|GRAY|GREY|Critical|High|Medium|Low)\]\s*"
        r"(?:([A-Za-z0-9 &/()\-]+?)\s*:\s*)?(.+)",
        re.IGNORECASE,
    )
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        m = block_re.match(lines[i].strip())
        if not m:
            i += 1
            continue
        severity = _normalise_severity(m.group(1))
        chapter = (m.group(2) or "").strip() or None
        title = m.group(3).strip()

        # Collect body lines until the next ALERT marker.
        body: list[str] = []
        j = i + 1
        while j < n and not block_re.match(lines[j].strip()):
            body.append(lines[j])
            j += 1
        body_text = "\n".join(body).strip()

        description, recommendation = _split_body(body_text)
        combined = f"{title}\n{body_text}"
        alert = ParsedAlert(
            title=title,
            severity=severity,
            chapter=chapter,
            description=description or None,
            recommendation=recommendation or None,
            sap_note_refs=_extract_notes(combined),
            tags=_auto_tags(combined),
        )
        result.alerts.append(alert)
        i = j


def _split_body(body: str) -> tuple[str, str]:
    """Split an alert body into description / recommendation parts."""
    description, recommendation = body, ""
    rec_match = re.search(r"(?is)Recommendation\s*[:\-]?\s*(.+)", body)
    if rec_match:
        recommendation = rec_match.group(1).strip()
        description = body[: rec_match.start()].strip()
    description = re.sub(r"(?i)^Description\s*[:\-]?\s*", "", description).strip()
    return description, recommendation


def parse_ewa_text(text: str) -> ParsedReport:
    """Parse EWA content from already-extracted text."""
    result = ParsedReport(raw_text=text)
    _parse_metadata(text, result)
    _parse_ratings(text, result)
    _parse_alerts(text, result)
    if result.overall_rating is None and result.ratings:
        # Derive overall rating as the worst chapter rating.
        worst = max(result.ratings, key=lambda r: _severity_score(r.rating))
        result.overall_rating = worst.rating
    return result


def _apply_filename_metadata(parsed: "ParsedReport", filename: str) -> None:
    """Fill missing sid / date / overall rating from the EWA filename.

    SAP encodes these reliably in the filename
    (``SID_installation_customer_YYYY-MM-DD_<R|Y|G>_EWA.DOC``), which is more
    dependable than scraping a cover page, so it is used whenever the parsed
    document did not yield the value.
    """
    from app.services.wordml_parser import parse_filename_metadata

    meta = parse_filename_metadata(filename)
    if not parsed.sid and meta["sid"]:
        parsed.sid = meta["sid"]
    if not parsed.report_date and meta["report_date"]:
        parsed.report_date = meta["report_date"]
    if not parsed.overall_rating and meta["overall_rating"]:
        parsed.overall_rating = meta["overall_rating"]


def parse_ewa_document(data: bytes, filename: str = "") -> ParsedReport:
    """Parse an EWA document from raw bytes (WordML .DOC / PDF / HTML / text)."""
    from app.services.wordml_parser import is_wordml, parse_wordml

    if is_wordml(data):
        parsed = parse_wordml(data)
    else:
        text = extract_text(data, filename)
        parsed = parse_ewa_text(text)
    _apply_filename_metadata(parsed, filename)
    return parsed
