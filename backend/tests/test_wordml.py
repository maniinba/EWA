"""Tests for the WordML (.DOC) EWA parser helpers and filename metadata."""
from __future__ import annotations

import struct
from datetime import date

from app.services.wordml_parser import (
    _classify_gif,
    is_wordml,
    parse_filename_metadata,
)


def _solid_gif(r: int, g: int, b: int) -> bytes:
    """Build a minimal 1x1 GIF with a 2-colour global table (colour + white)."""
    header = b"GIF89a"
    # logical screen descriptor: 1x1, GCT flag set, size=2 colours
    lsd = struct.pack("<HH", 1, 1) + bytes([0x80 | 0x00, 0, 0])  # size field 0 -> 2 colours
    palette = bytes([r, g, b, 255, 255, 255])
    body = b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
    return header + lsd + palette + body


def test_classify_gif_colors():
    assert _classify_gif(_solid_gif(128, 0, 0)) == "red"
    assert _classify_gif(_solid_gif(255, 153, 153)) == "red"
    assert _classify_gif(_solid_gif(232, 210, 88)) == "yellow"
    assert _classify_gif(_solid_gif(146, 192, 0)) == "green"
    assert _classify_gif(_solid_gif(0, 128, 0)) == "green"
    # Pure grays fall back to gray.
    assert _classify_gif(_solid_gif(200, 200, 200)) == "gray"


def test_classify_gif_non_gif():
    assert _classify_gif(b"\x89PNG\r\n\x1a\n") is None


def test_filename_metadata_full_pattern():
    meta = parse_filename_metadata("VSP_20708675_800734374_2026-08-10_R_EWA.DOC")
    assert meta["sid"] == "VSP"
    assert meta["report_date"] == date(2026, 8, 10)
    assert meta["overall_rating"] == "red"


def test_filename_metadata_yellow_and_alnum_sid():
    meta = parse_filename_metadata("VP1_21361177_500518283_2026-08-10_Y_EWA.DOC")
    assert meta["sid"] == "VP1"
    assert meta["overall_rating"] == "yellow"
    assert meta["report_date"] == date(2026, 8, 10)


def test_filename_metadata_with_path():
    meta = parse_filename_metadata(r"C:\Users\me\Downloads\VEP_20708674_312167679_2026-08-10_G_EWA.DOC")
    assert meta["sid"] == "VEP"
    assert meta["overall_rating"] == "green"


def test_filename_metadata_unknown():
    meta = parse_filename_metadata("random_file.pdf")
    assert meta["sid"] is None
    assert meta["report_date"] is None


def test_is_wordml_detection():
    assert is_wordml(b'<?xml version="1.0"?><?mso-application progid="Word.Document"?><w:wordDocument')
    assert not is_wordml(b"%PDF-1.7 ...")
    assert not is_wordml(b"plain text report")
