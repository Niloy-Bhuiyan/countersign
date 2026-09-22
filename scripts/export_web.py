"""Run the pipeline and write everything the web console and a BI tool read.

    python -m scripts.export_web

Writes to ``web/public``:

* ``data/queue.json``          one compact row per document, for the review queue
* ``data/case/<id>.json``      the full case: fields, findings, recommendation
* ``data/summary.json``        dashboard figures, all computed from the cases
* ``data/evaluation.json``     the committed evaluation results, for the method page
* ``exports/lines.csv|.xlsx``  one row per invoice line, shaped for a BI tool
* ``documents/``               the source files, so a reviewer can open the original

Nothing here is estimated. Every figure the console shows is computed from the
cases produced by this run, or read from ``eval/results``.
"""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from countersign import states
from countersign.agent.graph import recommend
from countersign.agent.tools import Toolbox
from countersign.batch import run_batch
from countersign.money import money
from countersign.reference import load
from data.catalogue import BY_SKU

CORPUS = Path("data/corpus")
OUT = Path("web/public")
DATA = OUT / "data"


def _s(value) -> str | None:
    return None if value is None else str(value)


def _category(sku: str | None) -> str:
    item = BY_SKU.get(sku or "")
    return item.category if item else "Uncategorised"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")


def main() -> None:
    reference = load(CORPUS)
    cases = run_batch(CORPUS / "documents", reference)

    toolbox = Toolbox(reference=reference, cases={})
    recommendations = {}
    for case in cases:
        if case.results:
            recommendations[case.document_id] = recommend(case, toolbox)
        toolbox.cases[case.document_id] = case

    if DATA.exists():
        shutil.rmtree(DATA)
    queue, lines_out = [], []
    spend_by_month = defaultdict(Decimal)
    spend_by_category = defaultdict(Decimal)
    held_by_vendor = defaultdict(Decimal)
    rule_counts = Counter()
    abstain_counts = Counter()
    action_counts = Counter()

    for case in cases:
        invoice = case.invoice
        vendor = reference.vendors.get(case.vendor_id or "")
        order = reference.orders.get(case.po_id or "")
        rec = recommendations.get(case.document_id)
        failed = [r for r in case.results if r.outcome == "failed"]
        abstained = [r for r in case.results if r.outcome == "abstained"]
        for r in failed:
            rule_counts[f"{r.check_code}/{r.rule}"] += 1
        for r in abstained:
            abstain_counts[f"{r.check_code}/{r.rule}"] += 1
        action = rec["action"] if rec else "REVIEW_MANUALLY"
        action_counts[action] += 1

        total = invoice.total if invoice else None
        category = _category(invoice.lines[0].sku) if invoice and invoice.lines else None
        row = {
            "id": case.document_id,
            "file": case.filename,
            "format": case.filename.rsplit(".", 1)[-1],
            "number": invoice.invoice_number if invoice else None,
            "vendor": vendor.legal_name if vendor else (invoice.vendor_name if invoice else None),
            "vendorId": case.vendor_id,
            "po": order.po_number if order else (invoice.purchase_order_ref if invoice else None),
            "issued": invoice.invoice_date.isoformat() if invoice else None,
            "currency": invoice.currency if invoice else None,
            "total": _s(total),
            "category": category,
            "state": case.state,
            "reason": case.review_reason,
            "action": action,
            "failed": sorted({f"{r.check_code}/{r.rule}" for r in failed}),
            "abstained": sorted({f"{r.check_code}/{r.rule}" for r in abstained}),
        }
        queue.append(row)

        if invoice and invoice.currency == "BDT":
            spend_by_month[invoice.invoice_date.strftime("%Y-%m")] += invoice.total
            for line in invoice.lines:
                spend_by_category[_category(line.sku)] += line.line_total
            if case.state == states.NEEDS_REVIEW and vendor:
                held_by_vendor[vendor.legal_name] += invoice.total

        if invoice:
            for line in invoice.lines:
                lines_out.append(
                    {
                        "document_id": case.document_id,
                        "invoice_number": invoice.invoice_number,
                        "vendor": vendor.legal_name if vendor else invoice.vendor_name,
                        "purchase_order": order.po_number if order else "",
                        "invoice_date": invoice.invoice_date.isoformat(),
                        "period": invoice.invoice_date.strftime("%Y-%m"),
                        "currency": invoice.currency,
                        "category": _category(line.sku),
                        "sku": line.sku or "",
                        "description": line.description,
                        "quantity": str(line.quantity),
                        "unit_price": str(line.unit_price),
                        "line_total": str(line.line_total),
                        "state": case.state,
                        "recommended_action": action,
                        "findings": "; ".join(sorted({f"{r.check_code}/{r.rule}" for r in failed})),
                        "synthetic": "yes",
                    }
                )

        detail = {
            **row,
            "history": case.history,
            "extraction": {
                "provider": case.extraction.provider,
                "version": case.extraction.version,
                "intake": case.extraction.intake.status,
                "sha256": case.extraction.intake.sha256,
                "failures": [f.model_dump() for f in case.extraction.failures],
            },
            "invoice": None
            if not invoice
            else {
                "vendorAsPrinted": invoice.vendor_name,
                "taxId": invoice.vendor_tax_id,
                "due": invoice.due_date.isoformat() if invoice.due_date else None,
                "subtotal": _s(invoice.subtotal),
                "tax": _s(invoice.tax_total),
                "total": _s(invoice.total),
                "lines": [
                    {
                        "no": line.line_no,
                        "sku": line.sku,
                        "description": line.description,
                        "uom": line.uom,
                        "quantity": _s(line.quantity),
                        "unitPrice": _s(line.unit_price),
                        "lineTotal": _s(line.line_total),
                        "taxRate": _s(line.tax_rate),
                    }
                    for line in invoice.lines
                ],
            },
            "order": None
            if not order
            else {
                "number": order.po_number,
                "orderedAt": order.ordered_at.isoformat(),
                "currency": order.currency,
                "lines": [
                    {
                        "no": line.line_no,
                        "sku": line.sku,
                        "description": line.description,
                        "quantity": _s(line.quantity),
                        "unitPrice": _s(line.unit_price),
                        "taxRate": _s(line.tax_rate),
                    }
                    for line in order.lines
                ],
                "deliveries": [
                    {
                        "id": d.id,
                        "number": d.delivery_note_number,
                        "date": d.delivered_at.isoformat(),
                        "lines": [
                            {"poLine": dl.po_line_no, "received": _s(dl.quantity_received)}
                            for dl in d.lines
                        ],
                    }
                    for d in reference.deliveries(order.id)
                ],
            },
            "results": [r.as_dict() for r in case.results],
            "recommendation": rec,
        }
        _write(DATA / "case" / f"{case.document_id}.json", detail)

    queue.sort(key=lambda r: (r["state"] == states.CLEARED, r["issued"] or "", r["id"]))
    _write(DATA / "queue.json", queue)

    bdt_open = [c for c in cases if c.invoice and c.invoice.currency == "BDT"]
    summary = {
        "documents": len(cases),
        "cleared": sum(1 for c in cases if c.state == states.CLEARED),
        "needsReview": sum(1 for c in cases if c.state == states.NEEDS_REVIEW),
        "spendBDT": _s(money(sum((c.invoice.total for c in bdt_open), Decimal(0)))),
        "atRiskBDT": _s(
            money(
                sum(
                    (c.invoice.total for c in bdt_open if c.state == states.NEEDS_REVIEW),
                    Decimal(0),
                )
            )
        ),
        "withFindings": sum(1 for c in cases if any(r.outcome == "failed" for r in c.results)),
        "spendByMonth": [
            {"period": k, "value": _s(money(v))} for k, v in sorted(spend_by_month.items())
        ],
        "spendByCategory": sorted(
            ({"label": k, "value": _s(money(v))} for k, v in spend_by_category.items()),
            key=lambda item: -Decimal(item["value"]),
        ),
        "heldByVendor": sorted(
            ({"label": k, "value": _s(money(v))} for k, v in held_by_vendor.items()),
            key=lambda item: -Decimal(item["value"]),
        )[:8],
        "findingsByRule": [{"label": k, "value": v} for k, v in rule_counts.most_common()],
        "abstentionsByRule": [{"label": k, "value": v} for k, v in abstain_counts.most_common()],
        "actions": [{"label": k, "value": v} for k, v in action_counts.most_common()],
        "reasons": [
            {"label": k or "cleared", "value": v}
            for k, v in Counter(c.review_reason for c in cases).most_common()
        ],
    }
    _write(DATA / "summary.json", summary)

    evaluation = {
        name: json.loads((Path("eval/results") / f"{name}.json").read_text(encoding="utf-8"))
        for name in ("extraction", "checks-current", "checks-without-materiality-floor")
    }
    for name in ("checks-current", "checks-without-materiality-floor"):
        evaluation[name].pop("false_positives", None)
    _write(DATA / "evaluation.json", evaluation)

    exports = OUT / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    columns = list(lines_out[0])
    with (exports / "countersign-lines.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(lines_out)
    book = Workbook()
    sheet = book.active
    sheet.title = "lines"
    sheet.append(columns)
    for line in lines_out:
        sheet.append([line[c] for c in columns])
    book.save(exports / "countersign-lines.xlsx")

    documents = OUT / "documents"
    if documents.exists():
        shutil.rmtree(documents)
    shutil.copytree(CORPUS / "documents", documents)

    print(f"{len(queue)} cases, {len(lines_out)} export lines written to {OUT}")


if __name__ == "__main__":
    main()
