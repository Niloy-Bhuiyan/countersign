"""What every check returns, and the ledger of invoices already seen.

A check never returns just an outcome. It returns the observed value, the
expected value, the tolerance it applied and the records it consulted, because a
finding a controller cannot recompute by hand is not a finding (ADR-001).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

PASSED = "passed"
FAILED = "failed"
ABSTAINED = "abstained"

THREE_WAY_MATCH = "THREE_WAY_MATCH"
PRICE_VARIANCE = "PRICE_VARIANCE"
DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
TAX_ARITHMETIC = "TAX_ARITHMETIC"

ALL_CHECKS = (THREE_WAY_MATCH, PRICE_VARIANCE, DUPLICATE_INVOICE, TAX_ARITHMETIC)


@dataclass(frozen=True)
class CheckResult:
    check_code: str
    outcome: str
    explanation: str
    rule: str = ""
    line_no: int | None = None
    observed: Decimal | None = None
    expected: Decimal | None = None
    tolerance: Decimal | None = None
    evidence: dict[str, list[str]] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "check_code": self.check_code,
            "outcome": self.outcome,
            "rule": self.rule,
            "line_no": self.line_no,
            "observed": None if self.observed is None else str(self.observed),
            "expected": None if self.expected is None else str(self.expected),
            "tolerance": None if self.tolerance is None else str(self.tolerance),
            "explanation": self.explanation,
            "evidence": self.evidence,
        }


def passed(check_code: str, explanation: str, **evidence) -> CheckResult:
    return CheckResult(check_code, PASSED, explanation, evidence=evidence)


@dataclass
class SeenInvoice:
    """Enough of an earlier invoice to recognise a repeat of it."""

    document_id: str
    sha256: str
    vendor_id: str
    po_id: str | None
    invoice_number: str
    issued_at: date
    total: Decimal


@dataclass
class Ledger:
    """Invoices processed so far, in arrival order.

    ``billed`` counts quantities per purchase order line that have already been
    accepted by the quantity rule. An invoice that failed it does not consume the
    delivery, so a clean invoice that follows an overbilled one is not punished
    for its predecessor's defect.
    """

    seen: list[SeenInvoice] = field(default_factory=list)
    billed: dict[tuple[str, int], Decimal] = field(default_factory=dict)

    def billed_on(self, po_id: str, line_no: int) -> Decimal:
        return self.billed.get((po_id, line_no), Decimal(0))

    def bill(self, po_id: str, line_no: int, quantity: Decimal) -> None:
        key = (po_id, line_no)
        self.billed[key] = self.billed.get(key, Decimal(0)) + quantity

    def to_dict(self) -> dict:
        """A snapshot the live API loads, so an upload is checked against history."""
        return {
            "seen": [
                {
                    "document_id": s.document_id,
                    "sha256": s.sha256,
                    "vendor_id": s.vendor_id,
                    "po_id": s.po_id,
                    "invoice_number": s.invoice_number,
                    "issued_at": s.issued_at.isoformat(),
                    "total": str(s.total),
                }
                for s in self.seen
            ],
            "billed": [
                {"po_id": po_id, "line_no": line_no, "quantity": str(quantity)}
                for (po_id, line_no), quantity in self.billed.items()
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> Ledger:
        return cls(
            seen=[
                SeenInvoice(
                    document_id=s["document_id"],
                    sha256=s["sha256"],
                    vendor_id=s["vendor_id"],
                    po_id=s["po_id"],
                    invoice_number=s["invoice_number"],
                    issued_at=date.fromisoformat(s["issued_at"]),
                    total=Decimal(s["total"]),
                )
                for s in payload["seen"]
            ],
            billed={(b["po_id"], b["line_no"]): Decimal(b["quantity"]) for b in payload["billed"]},
        )


def normalise_number(invoice_number: str) -> str:
    """``INV-001`` and ``inv 001`` are the same invoice number."""
    return "".join(ch for ch in invoice_number.upper() if ch.isalnum())
