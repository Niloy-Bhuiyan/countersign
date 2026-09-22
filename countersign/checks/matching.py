"""Pair each invoice line with the purchase order line it bills.

SKU first. When the document carries no SKU, or one the order does not contain,
fall back to description similarity against a stated threshold. That threshold is
the single place in the checks where a judgement is encoded as a number, and it is
configuration, not a literal.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from countersign.extraction.schema import ExtractedLine
from countersign.reference import POLine, PurchaseOrder
from countersign.settings import settings


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.casefold().strip(), b.casefold().strip()).ratio()


def match_line(line: ExtractedLine, order: PurchaseOrder) -> tuple[POLine | None, str]:
    """Return the matched order line and how it was matched."""
    if line.sku:
        for po_line in order.lines:
            if po_line.sku == line.sku:
                return po_line, "sku"

    scored = [
        (_similarity(line.description, po_line.description), po_line) for po_line in order.lines
    ]
    if scored:
        score, best = max(scored, key=lambda item: item[0])
        if score >= settings.description_match_threshold:
            return best, f"description {score:.2f}"
    return None, "unmatched"
