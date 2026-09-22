"""Run a folder of supplier documents through the whole pipeline.

Documents are processed in the order the invoices are dated, which is the order an
accounts-payable team would have received them. That matters: duplicate detection
and the quantity rule both depend on what arrived earlier.

Every state change goes through ``states.transition``. Nothing here assigns a
state directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from countersign import states
from countersign.checks import duplicate, price_variance, tax, three_way
from countersign.checks.base import CheckResult, Ledger
from countersign.extraction.pipeline import ExtractionOutcome, extract_document
from countersign.extraction.schema import ExtractedInvoice
from countersign.reference import Reference

DOCUMENT_SUFFIXES = {".pdf", ".xlsx", ".csv"}


@dataclass
class Case:
    """One document's journey, and everything needed to explain it."""

    document_id: str
    filename: str
    extraction: ExtractionOutcome
    state: str = states.RECEIVED
    review_reason: str | None = None
    vendor_id: str | None = None
    po_id: str | None = None
    results: list[CheckResult] = field(default_factory=list)
    history: list[str] = field(default_factory=lambda: [states.RECEIVED])

    @property
    def invoice(self) -> ExtractedInvoice | None:
        return self.extraction.invoice

    def move(self, target: str, **guards) -> None:
        self.state = states.transition(self.state, target, **guards)
        self.history.append(self.state)


def _arrival_key(case: Case):
    invoice = case.invoice
    return (0, invoice.invoice_date, case.document_id) if invoice else (1, None, case.document_id)


def run_batch(
    directory: Path,
    reference: Reference,
    extractions: dict[str, ExtractionOutcome] | None = None,
    ledger: Ledger | None = None,
) -> list[Case]:
    """Process every document. ``extractions`` reuses earlier reads, keyed by filename.

    Pass a ``ledger`` to keep it afterwards: the export snapshots it so the live API
    checks new uploads against every invoice already seen.
    """
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in DOCUMENT_SUFFIXES)
    cached = extractions or {}
    cases = [
        Case(
            document_id=path.stem,
            filename=path.name,
            extraction=cached.get(path.name) or extract_document(path),
        )
        for path in paths
    ]
    cases.sort(key=_arrival_key)
    ledger = ledger if ledger is not None else Ledger()
    unread = unread_orders(cases)

    for case in cases:
        check_case(case, reference, ledger, unread)

    return cases


def unread_orders(cases: list[Case]) -> dict[str, list[str]]:
    """Orders cited by a document that failed extraction.

    The reader's rejected output is untrusted, so it is used only to hold other
    invoices on the same order back, never to clear anything.
    """
    unread: dict[str, list[str]] = {}
    for case in cases:
        raw = case.extraction.raw
        if not case.extraction.ok and raw is not None and raw.purchase_order_ref:
            unread.setdefault(raw.purchase_order_ref.strip(), []).append(case.document_id)
    return unread


def check_case(
    case: Case,
    reference: Reference,
    ledger: Ledger,
    unread: dict[str, list[str]] | None = None,
) -> Case:
    """Take one extracted case through identity, the four checks and the state machine.

    The batch and the live API both call this, so a document uploaded to the
    console is judged by exactly the code the evaluation measured.
    """
    if not case.extraction.ok:
        case.review_reason = case.extraction.review_reason
        case.move(states.NEEDS_REVIEW)
        return case
    case.move(states.EXTRACTED)

    invoice = case.invoice
    vendor, how = reference.identify_vendor(invoice.vendor_name, invoice.vendor_tax_id)
    if vendor is None:
        case.review_reason = how
        case.move(states.NEEDS_REVIEW)
        return case
    case.vendor_id = vendor.id
    order = reference.orders.get(invoice.purchase_order_ref or "")
    case.po_id = order.id if order else None

    case.results = [
        *three_way.run(
            invoice,
            vendor,
            order,
            reference,
            ledger,
            (unread or {}).get(order.id, []) if order else [],
        ),
        *price_variance.run(invoice, vendor, order, reference),
        *duplicate.run(
            invoice,
            vendor,
            order,
            reference,
            ledger,
            document_id=case.document_id,
            sha256=case.extraction.intake.sha256,
        ),
        *tax.run(invoice, order),
    ]
    case.move(states.CHECKED)

    outcomes = [result.outcome for result in case.results]
    if states.all_checks_passed(outcomes):
        case.move(states.CLEARED, check_outcomes=outcomes)
    else:
        case.review_reason = "check_findings"
        case.move(states.NEEDS_REVIEW)
    return case
