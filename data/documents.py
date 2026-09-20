"""Emit one document per invoice and record what was written.

The manifest this produces is the bridge between the corpus and ingestion: it says
which file holds which invoice, in what format, under which spelling of the
vendor's name, and whether the file is readable at all.

``expected_intake`` is what ingestion should conclude about the file, not what the
invoice says. A quarantined document still has an invoice behind it in the corpus;
that is how the routing report can distinguish "we could not read it" from "we read
it and it was fine".
"""

from __future__ import annotations

import random
from pathlib import Path

from data.invoices import Invoice
from data.records import Vendor
from data.render.mess import (
    vendor_name_variant,
    write_corrupt_pdf,
    write_encrypted_pdf,
    write_image_only_pdf,
)
from data.render.pdf import render as render_pdf
from data.render.sheets import format_for_invoice, render_csv, render_xlsx

DOCUMENTS_DIR = Path("data/corpus/documents")

N_IMAGE_ONLY = 6
N_CORRUPT = 2
N_ENCRYPTED = 1

EXTENSIONS = {"pdf": ".pdf", "xlsx": ".xlsx", "csv": ".csv"}


def _unreadable_assignments(rng: random.Random, invoices: list[Invoice]) -> dict[str, str]:
    """Pick which invoices arrive as files nobody can read.

    Only clean invoices are chosen. A defective invoice inside an unreadable file
    would be a defect the system had no chance to catch, which would depress recall
    for a reason that has nothing to do with the checks.
    """
    eligible = [inv.id for inv in invoices if inv.defect is None]
    picked = rng.sample(eligible, N_IMAGE_ONLY + N_CORRUPT + N_ENCRYPTED)
    assignments = {}
    for index, invoice_id in enumerate(picked):
        if index < N_IMAGE_ONLY:
            assignments[invoice_id] = "quarantined_image_only"
        elif index < N_IMAGE_ONLY + N_CORRUPT:
            assignments[invoice_id] = "quarantined_unreadable"
        else:
            assignments[invoice_id] = "quarantined_encrypted"
    return assignments


def emit(
    rng: random.Random,
    vendors: list[Vendor],
    invoices: list[Invoice],
    directory: Path = DOCUMENTS_DIR,
) -> list[dict]:
    by_vendor = {vendor.id: vendor for vendor in vendors}
    unreadable = _unreadable_assignments(rng, invoices)
    directory.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for invoice in invoices:
        vendor = by_vendor[invoice.vendor_id]
        written_name = vendor_name_variant(vendor, rng)
        intake = unreadable.get(invoice.id, "readable")

        if intake == "quarantined_image_only":
            path = write_image_only_pdf(directory / f"{invoice.id}.pdf")
            file_format = "pdf"
        elif intake == "quarantined_unreadable":
            path = write_corrupt_pdf(directory / f"{invoice.id}.pdf")
            file_format = "pdf"
        elif intake == "quarantined_encrypted":
            path = write_encrypted_pdf(directory / f"{invoice.id}.pdf", invoice.invoice_number)
            file_format = "pdf"
        else:
            file_format = format_for_invoice(invoice)
            path = directory / f"{invoice.id}{EXTENSIONS[file_format]}"
            if file_format == "pdf":
                render_pdf(invoice, vendor, path, vendor_name=written_name)
            elif file_format == "xlsx":
                render_xlsx(invoice, vendor, path, vendor_name=written_name)
            else:
                render_csv(invoice, vendor, path, vendor_name=written_name)

        manifest.append(
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "vendor_id": invoice.vendor_id,
                "vendor_name_as_written": written_name,
                "filename": path.name,
                "format": file_format,
                "expected_intake": intake,
                "bytes": path.stat().st_size,
            }
        )

    return manifest
