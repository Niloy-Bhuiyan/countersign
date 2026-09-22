"""Price variance against this vendor's own history for the item.

Robust statistics, per ADR-003: median as the centre and median absolute
deviation as the scale, so the outlier being looked for cannot widen the band
enough to hide itself.

    z = 0.6745 * (price - median) / MAD

A line fails only when it is both a statistical outlier and materially above
the median (``price_variance_min_pct``). A tight history makes MAD tiny, and on
the first run a 2.6% move scored z = 13.6 on a clean invoice: unusual, and not
money at risk. The evaluation keeps the run without the floor for comparison.

Only prices *above* history fail. A price below what the vendor usually charges is
not money at risk, and flagging it would fill the queue with good news.

The check abstains, rather than guessing, when the history has fewer than
``price_history_min_points`` observations or when every past price was identical
(MAD of zero, where any deviation is infinitely many MADs).
"""

from __future__ import annotations

from decimal import Decimal
from statistics import median

from countersign.checks.base import ABSTAINED, FAILED, PRICE_VARIANCE, CheckResult, passed
from countersign.checks.matching import match_line
from countersign.extraction.schema import ExtractedInvoice
from countersign.money import money, pct_deviation
from countersign.reference import PurchaseOrder, Reference, Vendor
from countersign.settings import settings

CONSISTENCY = Decimal("0.6745")


def run(
    invoice: ExtractedInvoice,
    vendor: Vendor,
    order: PurchaseOrder | None,
    reference: Reference,
) -> list[CheckResult]:
    if order is None:
        return [
            CheckResult(
                PRICE_VARIANCE,
                ABSTAINED,
                "No order to date the price history against.",
                rule="no_order",
            )
        ]

    results: list[CheckResult] = []
    judged = 0
    for line in invoice.lines:
        po_line, _ = match_line(line, order)
        sku = po_line.sku if po_line else line.sku
        if not sku:
            continue
        history = reference.price_history(
            vendor.id, sku, order.ordered_at, settings.price_history_window_days
        )
        prices = [price for _, _, price in history]
        evidence = {"purchase_orders": [po_id for po_id, _, _ in history]}

        if len(prices) < settings.price_history_min_points:
            results.append(
                CheckResult(
                    PRICE_VARIANCE,
                    ABSTAINED,
                    f"Line {line.line_no}: only {len(prices)} earlier price(s) for {sku} from "
                    f"this vendor; {settings.price_history_min_points} are needed to judge.",
                    rule="insufficient_history",
                    line_no=line.line_no,
                    evidence=evidence,
                )
            )
            continue

        centre = median(prices)
        mad = median(abs(price - centre) for price in prices)
        if mad == 0:
            results.append(
                CheckResult(
                    PRICE_VARIANCE,
                    ABSTAINED,
                    f"Line {line.line_no}: every earlier price for {sku} was {centre}; "
                    "no spread to measure against.",
                    rule="zero_spread",
                    line_no=line.line_no,
                    evidence=evidence,
                )
            )
            continue

        judged += 1
        z = (CONSISTENCY * (line.unit_price - centre) / mad).quantize(Decimal("0.01"))
        above = pct_deviation(line.unit_price, centre).quantize(Decimal("0.1"))
        if z > settings.price_variance_mad_threshold and above > settings.price_variance_min_pct:
            results.append(
                CheckResult(
                    PRICE_VARIANCE,
                    FAILED,
                    f"Line {line.line_no}: {sku} at {line.unit_price} against a median of "
                    f"{money(centre)} over {len(prices)} earlier orders, {above}% above it; "
                    f"robust z {z} exceeds {settings.price_variance_mad_threshold}.",
                    rule="above_history",
                    line_no=line.line_no,
                    observed=line.unit_price,
                    expected=money(centre),
                    tolerance=settings.price_variance_mad_threshold,
                    evidence=evidence,
                )
            )

    if results:
        return results
    return [
        passed(
            PRICE_VARIANCE,
            f"All {judged} line(s) are within the vendor's own price history.",
        )
    ]
