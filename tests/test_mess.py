"""The messy fixtures have to be messy in the intended way and no other."""

import random

import pdfplumber
import pytest
from pdfplumber.utils.exceptions import PdfminerException

from countersign.vendors import normalise_vendor_name
from data.render.mess import (
    vendor_name_variant,
    write_corrupt_pdf,
    write_encrypted_pdf,
    write_image_only_pdf,
)


def test_every_name_variant_normalises_to_the_same_key(corpus):
    """If this fails, duplicate detection quietly stops working for that vendor."""
    rng = random.Random(7)
    for vendor in corpus["vendors"]:
        expected = normalise_vendor_name(vendor.legal_name)
        for _ in range(40):
            variant = vendor_name_variant(vendor, rng)
            assert normalise_vendor_name(variant) == expected, f"{vendor.legal_name} -> {variant!r}"


def test_variants_actually_vary(corpus):
    rng = random.Random(7)
    vendor = next(v for v in corpus["vendors"] if v.legal_name.endswith(" Ltd"))
    seen = {vendor_name_variant(vendor, rng) for _ in range(60)}
    assert len(seen) > 1


def test_a_corrupt_pdf_cannot_be_opened(tmp_path):
    # Named rather than blind: ingestion has to catch exactly this to quarantine
    # the file instead of failing the whole batch.
    path = write_corrupt_pdf(tmp_path / "corrupt.pdf")
    with pytest.raises(PdfminerException, match="Is this really a PDF"):
        with pdfplumber.open(path) as pdf:
            pdf.pages[0].extract_text()


def test_an_encrypted_pdf_cannot_be_read_without_the_password(tmp_path):
    path = write_encrypted_pdf(tmp_path / "locked.pdf", "INV-0001")
    with pytest.raises(PdfminerException):
        with pdfplumber.open(path) as pdf:
            pdf.pages[0].extract_text()


def test_an_image_only_page_yields_no_text(tmp_path):
    path = write_image_only_pdf(tmp_path / "scan.pdf")
    with pdfplumber.open(path) as pdf:
        assert not (pdf.pages[0].extract_text() or "").strip()
