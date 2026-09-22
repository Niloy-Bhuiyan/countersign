"""Open a supplier document, or decide it cannot be opened.

Intake never raises on a bad file. A corrupt, encrypted or image-only document is
a normal event in an accounts-payable inbox; failing the batch over one would be
worse than the document itself. Each is given a quarantine status and routed to a
person, and the reason is recorded so the routing report can count it.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from openpyxl import load_workbook
from pdfplumber.utils.exceptions import PdfminerException

READABLE = "readable"
UNREADABLE = "quarantined_unreadable"
ENCRYPTED = "quarantined_encrypted"
IMAGE_ONLY = "quarantined_image_only"


@dataclass
class Intake:
    path: Path
    sha256: str
    media_type: str
    status: str
    #: Text layer for a PDF, one string per page.
    pages: list[str] = field(default_factory=list)
    #: Cell values for a spreadsheet or CSV, one list per row, all as strings.
    rows: list[list[str]] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return self.status == READABLE


def _cells(values) -> list[str]:
    return ["" if value is None else str(value).strip() for value in values]


def read(path: Path) -> Intake:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    suffix = path.suffix.lower()

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            rows = [_cells(row) for row in csv.reader(handle)]
        return Intake(path, digest, "text/csv", READABLE, rows=rows)

    if suffix == ".xlsx":
        sheet = load_workbook(path, read_only=True, data_only=True).active
        rows = [_cells(row) for row in sheet.iter_rows(values_only=True)]
        return Intake(
            path,
            digest,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            READABLE,
            rows=rows,
        )

    # PDF. An encrypted file announces itself in the trailer before any parser
    # runs, which lets it be told apart from one that is merely broken.
    if b"/Encrypt" in data:
        return Intake(path, digest, "application/pdf", ENCRYPTED)
    try:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except PdfminerException:
        return Intake(path, digest, "application/pdf", UNREADABLE)

    if not any(page.strip() for page in pages):
        return Intake(path, digest, "application/pdf", IMAGE_ONLY)
    return Intake(path, digest, "application/pdf", READABLE, pages=pages)
