"""Parser for SAP EarlyWatch Alert reports exported as Word 2003 XML (.DOC).

SAP for Me exports EWA reports in the WordprocessingML format (``.DOC`` files
that are actually ``<?xml ...><w:wordDocument>`` documents, *not* the legacy
binary Word format). The important content lives in two tables:

* **Alert Overview** - one row per finding: a colour-icon rating cell followed
  by the finding text.
* **Check Overview** - topic / subtopic ratings, again encoded as colour icons.

Ratings are embedded GIF icons (no text/alt), so severity is recovered by
decoding each icon's colour palette and classifying its hue. Report SID, date
and overall rating are taken from the filename, which SAP encodes reliably as
``SID_installation_customer_YYYY-MM-DD_<R|Y|G>_EWA.DOC``.
"""
from __future__ import annotations

import base64
import colorsys
import re
import xml.etree.ElementTree as ET
from io import BytesIO

W = "{http://schemas.microsoft.com/office/word/2003/wordml}"
V = "{urn:schemas-microsoft-com:vml}"


def is_wordml(data: bytes) -> bool:
    head = data[:4000].lstrip()
    return head[:5] == b"<?xml" and b"wordDocument" in data[:6000]


# --------------------------------------------------------------------------- #
# Rating-icon colour classification
# --------------------------------------------------------------------------- #
def _classify_gif(data: bytes) -> str | None:
    """Classify a rating icon (GIF) as red / yellow / green / gray by hue."""
    if data[:3] != b"GIF":
        return None
    flags = data[10]
    if not (flags & 0x80):  # no global colour table
        return None
    size = 2 ** ((flags & 0x07) + 1)
    pal = data[13 : 13 + size * 3]
    best_hue = None
    best_score = -1.0
    for i in range(0, len(pal) - 2, 3):
        r, g, b = pal[i], pal[i + 1], pal[i + 2]
        if (r, g, b) == (255, 0, 255):  # magenta = transparency marker
            continue
        mx, mn = max(r, g, b), min(r, g, b)
        if mx < 40 or mn > 210 or (mx - mn) < 30:  # black / white / gray
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        score = s * v
        if score > best_score:
            best_score = score
            best_hue = h * 360
    if best_hue is None:
        return "gray"
    if best_hue < 40 or best_hue >= 320:
        return "red"
    if best_hue < 68:
        return "yellow"
    if best_hue < 200:
        return "green"
    return "gray"


# --------------------------------------------------------------------------- #
# Low-level WordML helpers
# --------------------------------------------------------------------------- #
def _para_text(el) -> str:
    return "".join(t.text or "" for t in el.iter(W + "t")).strip()


def _cell_text(tc) -> str:
    return " ".join(t.text or "" for t in tc.iter(W + "t")).strip()


def _cell_imgs(tc) -> list[str]:
    return [im.get("src") for im in tc.iter(V + "imagedata") if im.get("src")]


def _collect_bindata(root) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for bd in root.iter(W + "binData"):
        name = bd.get(W + "name")
        if name and bd.text:
            try:
                out[name] = base64.b64decode(re.sub(r"\s", "", bd.text))
            except (ValueError, base64.binascii.Error):  # type: ignore[attr-defined]
                continue
    return out


# --------------------------------------------------------------------------- #
# Table classification
# --------------------------------------------------------------------------- #
def _rows(tbl):
    return tbl.findall(W + "tr")


def _alert_row_count(tbl) -> int:
    """Count rows shaped like an Alert Overview entry: [icon][text]."""
    hits = 0
    for tr in _rows(tbl):
        cells = tr.findall(W + "tc")
        if (
            len(cells) == 2
            and _cell_imgs(cells[0])
            and _cell_text(cells[1])
            and not _cell_text(cells[0])
        ):
            hits += 1
    return hits


def _is_check_overview(tbl) -> bool:
    header = " ".join(_cell_text(tc) for tc in (_rows(tbl)[0].findall(W + "tc") if _rows(tbl) else []))
    return "Topic Rating" in header and "Subtopic" in header


# --------------------------------------------------------------------------- #
# Chapter inference
# --------------------------------------------------------------------------- #
_CHAPTER_RULES = [
    ("Security", ["security", "password", "authorization", "authorisation", "privilege",
                  "gateway", "audit", "encryption", "default passwords", "reg_info",
                  "critical authorizations", "outdated", "security note"]),
    ("HANA / Database", ["hana", "database", "index", "sql statement", "delta", "records",
                         "tablespace", "backup", "db "]),
    ("Performance", ["response time", "performance", "workload", "dialog", "throughput",
                     "expensive sql"]),
    ("Basis / Operations", ["abap dump", "dumps", "update error", "rtcctool", "kernel",
                            "number range", "job", "spool", "background"]),
    ("Configuration", ["configuration", "maintenance", "support package", "parameter",
                       "note assistant", "fiori"]),
    ("Hardware", ["hardware", "cpu", "memory", "paging", "capacity"]),
]


def _infer_chapter(text: str) -> str:
    low = text.lower()
    for chapter, kws in _CHAPTER_RULES:
        if any(k in low for k in kws):
            return chapter
    return "General"


def _auto_tags(text: str) -> list[str]:
    low = text.lower()
    tags = []
    for chapter, kws in _CHAPTER_RULES:
        if any(k in low for k in kws):
            tags.append(chapter.split(" /")[0].split(" ")[0])
    return sorted(set(tags))


# --------------------------------------------------------------------------- #
# Main parse
# --------------------------------------------------------------------------- #
def parse_wordml(data: bytes):
    """Parse a WordML EWA document into a ParsedReport (imported lazily to
    avoid a circular import with pdf_parser)."""
    from app.services.pdf_parser import ParsedAlert, ParsedRating, ParsedReport

    root = ET.parse(BytesIO(data)).getroot()
    bindata = _collect_bindata(root)
    color_cache: dict[str, str | None] = {}

    def color_of(src: str) -> str | None:
        if src not in color_cache:
            blob = bindata.get(src)
            color_cache[src] = _classify_gif(blob) if blob else None
        return color_cache[src]

    # Full paragraph list (for detail lookup / SAP notes / metadata fallback).
    all_paras = [txt for _kind, txt in _iter_all_paras(root)]

    result = ParsedReport(raw_text="\n".join(all_paras))

    # The Alert Overview / Check Overview tables can be nested inside layout
    # tables, so scan every table and pick the best-matching candidate rather
    # than relying on document position.
    alerts: list[ParsedAlert] = []
    ratings: list[ParsedRating] = []
    best_alert_rows = 0
    best_rating_rows = 0
    for tbl in root.iter(W + "tbl"):
        if _is_check_overview(tbl):
            parsed_ratings = _parse_check_overview(tbl, color_of)
            if len(parsed_ratings) > best_rating_rows:
                best_rating_rows = len(parsed_ratings)
                ratings = parsed_ratings
            continue
        row_hits = _alert_row_count(tbl)
        if row_hits >= 3 and row_hits > best_alert_rows:
            best_alert_rows = row_hits
            alerts = _parse_alert_table(tbl, color_of)

    # De-duplicate ratings by chapter (keep worst).
    result.ratings = _dedupe_ratings(ratings)
    result.alerts = alerts

    # Metadata best-effort from the cover table (filename fallback added later).
    result.system_type = _detect_system_type(all_paras)
    return result


def _iter_all_paras(root):
    for p in root.iter(W + "p"):
        txt = _para_text(p)
        if txt:
            yield ("p", txt)


_SEV_MAP = {"red": "red", "yellow": "yellow", "green": "green", "gray": "gray"}


def _parse_alert_table(tbl, color_of):
    from app.services.pdf_parser import ParsedAlert

    out = []
    seen = set()
    for tr in _rows(tbl):
        cells = tr.findall(W + "tc")
        if len(cells) != 2:
            continue
        imgs = _cell_imgs(cells[0])
        text = _cell_text(cells[1])
        if not imgs or not text or _cell_text(cells[0]):
            continue
        if text in seen:
            continue
        seen.add(text)
        sev = color_of(imgs[0]) or "yellow"
        out.append(
            ParsedAlert(
                title=text,
                severity=_SEV_MAP.get(sev, "yellow"),
                chapter=_infer_chapter(text),
                tags=_auto_tags(text),
                sap_note_refs=[],
            )
        )
    return out


def _parse_check_overview(tbl, color_of):
    from app.services.pdf_parser import ParsedRating

    out = []
    score = {"red": 3, "yellow": 2, "green": 1, "gray": 0}
    for tr in _rows(tbl):
        cells = tr.findall(W + "tc")
        if len(cells) < 2:
            continue
        # Top-level topic: icon in col0, name in col1.
        topic_imgs = _cell_imgs(cells[0])
        topic_name = _cell_text(cells[1])
        if topic_imgs and topic_name:
            color = color_of(topic_imgs[0]) or "gray"
            out.append(ParsedRating(chapter=topic_name, rating=color, score=score.get(color, 0)))
    return out


def _dedupe_ratings(ratings):
    score = {"red": 3, "yellow": 2, "green": 1, "gray": 0}
    best: dict[str, object] = {}
    for r in ratings:
        cur = best.get(r.chapter)
        if cur is None or score.get(r.rating, 0) > score.get(cur.rating, 0):
            best[r.chapter] = r
    return list(best.values())


def _detect_system_type(paras) -> str | None:
    joined = " ".join(paras[:80]).lower()
    if "s/4hana" in joined or "s4hana" in joined:
        return "S/4HANA"
    if "hana database" in joined or "sap hana" in joined:
        return "HANA"
    if "netweaver" in joined or "abap" in joined:
        return "ABAP"
    return None


# --------------------------------------------------------------------------- #
# Filename metadata
# --------------------------------------------------------------------------- #
_FILENAME_RE = re.compile(
    r"(?P<sid>[A-Z0-9]{3})[_-]\d+[_-]\d+[_-](?P<date>\d{4}-\d{2}-\d{2})[_-](?P<rating>[RYG])[_-]?EWA",
    re.IGNORECASE,
)
_RATING_LETTER = {"R": "red", "Y": "yellow", "G": "green"}


def parse_filename_metadata(filename: str) -> dict:
    """Extract sid / date / overall rating from an SAP EWA filename."""
    import datetime as _dt

    out: dict = {"sid": None, "report_date": None, "overall_rating": None}
    if not filename:
        return out
    base = filename.replace("\\", "/").split("/")[-1]
    m = _FILENAME_RE.search(base)
    if m:
        out["sid"] = m.group("sid").upper()
        out["overall_rating"] = _RATING_LETTER.get(m.group("rating").upper())
        try:
            out["report_date"] = _dt.date.fromisoformat(m.group("date"))
        except ValueError:
            pass
        return out
    # Fallbacks: a 3-char leading token and any ISO date in the name.
    lead = re.match(r"([A-Z0-9]{3})[_-]", base, re.IGNORECASE)
    if lead:
        out["sid"] = lead.group(1).upper()
    dm = re.search(r"(\d{4}-\d{2}-\d{2})", base)
    if dm:
        try:
            out["report_date"] = _dt.date.fromisoformat(dm.group(1))
        except ValueError:
            pass
    return out
