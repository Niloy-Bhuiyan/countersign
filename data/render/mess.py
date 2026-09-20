"""The parts of the corpus that are supposed to be difficult.

Three kinds of mess, for three different reasons:

* **Vendor name variants.** The same supplier is written differently on different
  documents. Every variant here must normalise to the same key, which is asserted
  by a test; if one does not, duplicate detection silently stops working for that
  vendor.
* **Unreadable files.** A corrupt PDF, a password-protected one, and a page with
  no text layer. These exist so that intake has to quarantine rather than crash,
  and so the routing report has a category for documents nobody could read.
* **Formatting noise.** Trailing whitespace and inconsistent thousands separators,
  which is what actually breaks a parser that trusts its input.

Nothing here alters what an invoice *says*. A document made messy is still the
same invoice, and still carries whatever defect it was given, or none.
"""

from __future__ import annotations

import random
from pathlib import Path

from reportlab.lib import pdfencrypt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

from data.records import Vendor

PAGE_W, PAGE_H = A4


def vendor_name_variant(vendor: Vendor, rng: random.Random) -> str:
    """One of the ways this supplier's name gets written.

    Only legal form, case, punctuation and spacing vary. Trade words are never
    added or removed, because that would make two different suppliers.
    """
    name = vendor.legal_name
    variants = [name]

    variants.append(name.upper())
    variants.append(name + " ")
    variants.append(name.replace(" ", "  ", 1))

    if name.endswith(" Ltd"):
        variants.append(name + ".")
        variants.append(name[: -len("Ltd")] + "Limited")
    if name.endswith(" Limited"):
        variants.append(name[: -len("Limited")] + "Ltd")
        variants.append(name[: -len("Limited")] + "Ltd.")
    if name.endswith(" Corporation"):
        variants.append(name[: -len("Corporation")] + "Corp.")
    if "& Sons" in name:
        variants.append(name.replace("& Sons", "and Sons"))

    return rng.choice(variants)


def write_corrupt_pdf(path: Path) -> Path:
    """A truncated file that claims to be a PDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%trunc")
    return path


def write_encrypted_pdf(path: Path, invoice_number: str) -> Path:
    """A PDF the supplier password-protected before sending it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encryption = pdfencrypt.StandardEncryption("countersign-synthetic", canPrint=1)
    c = pdfcanvas.Canvas(str(path), pagesize=A4, encrypt=encryption)
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, PAGE_H - 30 * mm, f"Protected invoice {invoice_number}")
    c.showPage()
    c.save()
    return path


def write_image_only_pdf(path: Path) -> Path:
    """A page that looks scanned and carries no text layer at all.

    Drawn as vector blocks rather than embedding a raster image: the effect on
    extraction is identical, ``pdfplumber`` returns nothing either way, and it
    avoids an image dependency for a file whose whole purpose is to be unreadable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    c = pdfcanvas.Canvas(str(path), pagesize=A4)
    c.setFillGray(0.35)
    rng = random.Random(path.name)
    y = PAGE_H - 30 * mm
    while y > 40 * mm:
        width = rng.uniform(40, 150) * mm
        c.rect(20 * mm, y, width, 2.2 * mm, stroke=0, fill=1)
        y -= rng.uniform(5, 9) * mm
    c.showPage()
    c.save()
    return path
