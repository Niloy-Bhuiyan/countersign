"""Run the pipeline and write everything the console, the API and a BI tool read.

    python -m scripts.export_web

Writes to ``web/public``:

* ``data/queue.json``          one compact row per corpus document
* ``data/case/<id>.json``      the full case, from ``countersign.serialize``
* ``data/summary.json``        controller figures, computed from the cases
* ``data/evaluation.json``     the committed evaluation results
* ``exports/countersign-lines.csv|.xlsx``  one row per invoice line
* ``documents/``               the source files

and to ``api/_data`` the snapshot the live API starts from: the buyer's records,
the ledger after every corpus invoice, orders with an unread document, and each
corpus case's state and recommendation (so a decision on it can be validated).

Nothing here is estimated.
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
from countersign.batch import run_batch, unread_orders
from countersign.checks.base import Ledger
from countersign.money import money
from countersign.reference import load
from countersign.serialize import case_detail, queue_row
from data.catalogue import BY_SKU

CORPUS = Path("data/corpus")
OUT = Path("web/public")
DATA = OUT / "data"
SNAPSHOT = Path("api/_data")


def category_of(sku: str | None) -> str:
    item = BY_SKU.get(sku or "")
    return item.category if item else "Uncategorised"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")


def _s(value) -> str:
    return str(money(value))


def main() -> None:
    reference = load(CORPUS)
    ledger = Ledger()
    cases = run_batch(CORPUS / "documents", reference, ledger=ledger)

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
    rule_counts, abstain_counts, action_counts = Counter(), Counter(), Counter()
    index = {}

    for case in cases:
        rec = recommendations.get(case.document_id)
        row = queue_row(case, reference, rec, category_of)
        queue.append(row)
        index[case.document_id] = {"state": case.state, "action": row["action"]}
        _write(
            DATA / "case" / f"{case.document_id}.json",
            case_detail(case, reference, rec, category_of),
        )

        action_counts[row["action"]] += 1
        for key in row["failed"]:
            rule_counts[key] += 1
        for key in row["abstained"]:
            abstain_counts[key] += 1

        invoice = case.invoice
        if not invoice:
            continue
        vendor = reference.vendors.get(case.vendor_id or "")
        order = reference.orders.get(case.po_id or "")
        if invoice.currency == "BDT":
            spend_by_month[invoice.invoice_date.strftime("%Y-%m")] += invoice.total
            for line in invoice.lines:
                spend_by_category[category_of(line.sku)] += line.line_total
            if case.state == states.NEEDS_REVIEW and vendor:
                held_by_vendor[vendor.legal_name] += invoice.total
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
                    "category": category_of(line.sku),
                    "sku": line.sku or "",
                    "description": line.description,
                    "quantity": str(line.quantity),
                    "unit_price": str(line.unit_price),
                    "line_total": str(line.line_total),
                    "state": case.state,
                    "recommended_action": row["action"],
                    "findings": "; ".join(row["failed"]),
                    "synthetic": "yes",
                }
            )

    queue.sort(key=lambda r: (r["state"] == states.CLEARED, r["issued"] or "", r["id"]))
    _write(DATA / "queue.json", queue)

    bdt = [c for c in cases if c.invoice and c.invoice.currency == "BDT"]
    _write(
        DATA / "summary.json",
        {
            "documents": len(cases),
            "cleared": sum(1 for c in cases if c.state == states.CLEARED),
            "needsReview": sum(1 for c in cases if c.state == states.NEEDS_REVIEW),
            "spendBDT": _s(sum((c.invoice.total for c in bdt), Decimal(0))),
            "atRiskBDT": _s(
                sum((c.invoice.total for c in bdt if c.state == states.NEEDS_REVIEW), Decimal(0))
            ),
            "withFindings": sum(1 for c in cases if any(r.outcome == "failed" for r in c.results)),
            "spendByMonth": [
                {"period": k, "value": _s(v)} for k, v in sorted(spend_by_month.items())
            ],
            "spendByCategory": sorted(
                ({"label": k, "value": _s(v)} for k, v in spend_by_category.items()),
                key=lambda item: -Decimal(item["value"]),
            ),
            "heldByVendor": sorted(
                ({"label": k, "value": _s(v)} for k, v in held_by_vendor.items()),
                key=lambda item: -Decimal(item["value"]),
            )[:8],
            "findingsByRule": [{"label": k, "value": v} for k, v in rule_counts.most_common()],
            "abstentionsByRule": [
                {"label": k, "value": v} for k, v in abstain_counts.most_common()
            ],
            "actions": [{"label": k, "value": v} for k, v in action_counts.most_common()],
            "reasons": [
                {"label": k or "cleared", "value": v}
                for k, v in Counter(c.review_reason for c in cases).most_common()
            ],
        },
    )

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

    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    for name in ("vendors.json", "purchase_orders.json", "deliveries.json"):
        shutil.copyfile(CORPUS / name, SNAPSHOT / name)
    _write(SNAPSHOT / "ledger.json", ledger.to_dict())
    _write(SNAPSHOT / "unread.json", unread_orders(cases))
    _write(SNAPSHOT / "cases.json", index)

    print(f"{len(queue)} cases, {len(lines_out)} export lines; API snapshot in {SNAPSHOT}")


if __name__ == "__main__":
    main()
