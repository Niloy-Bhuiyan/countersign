"""The evaluation harness. The only code allowed to read the ground truth.

    python -m eval.run

Reads each document once, then measures:

1. Extraction accuracy per field, against what each document actually says.
2. The reader alone (v1) against the reader with arithmetic validators (v2).
3. Exception detection per defect and per check, strict and any-check.
4. Routing: what cleared, what went to review and why, and how many planted
   defects reached ``cleared``.
5. False positives on clean invoices, as a rate and as a list.

Checks run under two configurations of the price-variance check, with and without
the materiality floor, and both results are kept (docs/evaluation.md, rule 3).
Everything under ``eval/results/`` and ``eval/report.md`` is regenerated here.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from countersign import states
from countersign.agent.graph import recommend
from countersign.agent.tools import Toolbox
from countersign.batch import DOCUMENT_SUFFIXES, run_batch
from countersign.extraction import offline
from countersign.extraction.pipeline import ExtractionOutcome
from countersign.extraction.schema import parse_raw
from countersign.extraction.validators import validate
from countersign.intake import read
from countersign.reference import load
from countersign.settings import settings
from countersign.vendors import normalise_vendor_name

CORPUS = Path("data/corpus")
DOCUMENTS = CORPUS / "documents"
TRUTH = Path("data/ground_truth/exceptions.json")
RESULTS = Path("eval/results")
REPORT = Path("eval/report.md")

FIELDS = (
    "invoice_number",
    "vendor",
    "vendor_tax_id",
    "invoice_date",
    "due_date",
    "purchase_order_ref",
    "currency",
    "line_count",
    "line_items",
    "subtotal",
    "tax_total",
    "total",
)


def _pct(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


def _field_scores(extracted, truth: dict, vendors: dict) -> dict[str, bool]:
    lines_ok = len(extracted.lines) == len(truth["lines"]) and all(
        line.quantity == Decimal(t["quantity"])
        and line.unit_price == Decimal(t["unit_price"])
        and line.line_total == Decimal(t["line_total"])
        for line, t in zip(extracted.lines, truth["lines"], strict=False)
    )
    vendor = vendors[truth["vendor_id"]]
    return {
        "invoice_number": extracted.invoice_number == truth["invoice_number"],
        "vendor": normalise_vendor_name(extracted.vendor_name) == vendor["normalised_name"],
        "vendor_tax_id": extracted.vendor_tax_id == vendor["tax_id"],
        "invoice_date": extracted.invoice_date.isoformat() == truth["issued_at"],
        "due_date": extracted.due_date is not None
        and extracted.due_date.isoformat() == truth["due_at"],
        "purchase_order_ref": extracted.purchase_order_ref == truth["po_id"],
        "currency": extracted.currency == truth["currency"],
        "line_count": len(extracted.lines) == len(truth["lines"]),
        "line_items": lines_ok,
        "subtotal": extracted.subtotal == Decimal(truth["subtotal"]),
        "tax_total": extracted.tax_total == Decimal(truth["tax_total"]),
        "total": extracted.total == Decimal(truth["total"]),
    }


def evaluate_extraction(truth_invoices: dict, vendors: dict):
    """Read every document once; score v1 and v2; return v2 outcomes for reuse."""
    correct = Counter()
    readable = 0
    v1 = Counter()
    v2 = Counter()
    outcomes: dict[str, ExtractionOutcome] = {}
    wrong_v1: list[str] = []

    for path in sorted(p for p in DOCUMENTS.iterdir() if p.suffix.lower() in DOCUMENT_SUFFIXES):
        intake = read(path)
        if not intake.readable:
            outcomes[path.name] = ExtractionOutcome(intake=intake)
            v1["quarantined"] += 1
            v2["quarantined"] += 1
            continue
        readable += 1
        truth = truth_invoices[path.stem]

        raw = offline.extract(intake)
        parsed = parse_raw(raw)

        if not parsed.ok:
            outcomes[path.name] = ExtractionOutcome(
                intake=intake, failures=parsed.failures, raw=raw
            )
            v1["routed_to_review"] += 1
            v2["routed_to_review"] += 1
            continue

        scores = _field_scores(parsed.invoice, truth, vendors)
        for name, ok in scores.items():
            correct[name] += ok
        fully_right = all(scores.values())

        v1["persisted_correct" if fully_right else "persisted_wrong"] += 1
        if not fully_right:
            wrong_v1.append(path.stem)

        failures = validate(parsed.invoice)
        if failures:
            v2["routed_to_review"] += 1
            outcomes[path.name] = ExtractionOutcome(intake=intake, failures=failures, raw=raw)
        else:
            v2["persisted_correct" if fully_right else "persisted_wrong"] += 1
            outcomes[path.name] = ExtractionOutcome(
                intake=intake,
                invoice=parsed.invoice,
                version=offline.VERSION + "+validators",
                raw=raw,
            )

    result = {
        "provider": offline.NAME,
        "reader_version": offline.VERSION,
        "documents": len(outcomes),
        "readable": readable,
        "per_field_accuracy": {name: _pct(correct[name], readable) for name in FIELDS},
        "v1_reader_only": dict(v1),
        "v2_reader_plus_validators": dict(v2),
        "v1_wrong_records": wrong_v1,
    }
    return result, outcomes


def evaluate_checks(cases, truth_rows: dict) -> dict:
    by_code = defaultdict(lambda: Counter())
    check_failures = Counter()
    check_true = Counter()
    check_expected = Counter()
    false_positives = []
    clean_abstention_only = 0
    clean_total = 0
    reasons = Counter()

    for case in cases:
        reasons[case.review_reason or "cleared"] += 1
        failed = [r for r in case.results if r.outcome == "failed"]
        failed_checks = {r.check_code for r in failed}
        truth = truth_rows.get(case.document_id)

        for code in failed_checks:
            check_failures[code] += 1
            if truth and truth["expected_check"] == code:
                check_true[code] += 1

        if truth:
            counts = by_code[truth["defect_code"]]
            counts["planted"] += 1
            check_expected[truth["expected_check"]] += 1
            counts["caught_by_expected_check"] += truth["expected_check"] in failed_checks
            counts["flagged_by_any_check"] += bool(failed_checks)
            counts["kept_out_of_cleared"] += case.state != states.CLEARED
        elif case.extraction.ok and case.review_reason not in ("vendor_ambiguous",):
            clean_total += 1
            if failed:
                false_positives.append(
                    {
                        "document_id": case.document_id,
                        "findings": [f"{r.check_code}/{r.rule}: {r.explanation}" for r in failed],
                    }
                )
            elif case.state == states.NEEDS_REVIEW:
                clean_abstention_only += 1

    per_check = {}
    for code in ("THREE_WAY_MATCH", "PRICE_VARIANCE", "DUPLICATE_INVOICE", "TAX_ARITHMETIC"):
        per_check[code] = {
            "fired": check_failures[code],
            "fired_on_its_own_defects": check_true[code],
            "defects_it_owns": check_expected[code],
            "recall_strict": _pct(check_true[code], check_expected[code]),
        }

    fp_by_rule = Counter(
        finding.split(":")[0] for fp in false_positives for finding in fp["findings"]
    )
    cleared = sum(1 for case in cases if case.state == states.CLEARED)
    defects_cleared = sum(
        1 for case in cases if case.document_id in truth_rows and case.state == states.CLEARED
    )
    planted = sum(c["planted"] for c in by_code.values())
    any_caught = sum(c["flagged_by_any_check"] for c in by_code.values())

    return {
        "documents": len(cases),
        "routing": {
            "cleared": cleared,
            "cleared_share": _pct(cleared, len(cases)),
            "by_reason": dict(reasons),
        },
        "defects": {
            "planted": planted,
            "reached_cleared": defects_cleared,
            "flagged_by_any_check": any_caught,
            "recall_any": _pct(any_caught, planted),
            "by_defect": {code: dict(counts) for code, counts in sorted(by_code.items())},
        },
        "per_check": per_check,
        "clean_invoices": {
            "checked": clean_total,
            "with_a_failed_check": len(false_positives),
            "false_positive_rate": _pct(len(false_positives), clean_total),
            "routed_only_because_a_check_abstained": clean_abstention_only,
            "false_positives_by_rule": dict(fp_by_rule),
        },
        "false_positives": false_positives,
    }


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _render_report(extraction: dict, configs: dict, actions: Counter) -> str:
    current = configs["current"]
    floorless = configs["without_materiality_floor"]
    lines = [
        "# Evaluation report",
        "",
        "Generated by `python -m eval.run`. Every number here comes from the result files in",
        "[`eval/results/`](results/). **All data is synthetic**; results on this corpus are an",
        "upper bound, not a prediction of performance on real invoices. See",
        "[docs/dataset-card.md](../docs/dataset-card.md#limitations).",
        "",
        "## Extraction",
        "",
        f"Offline reader `{extraction['reader_version']}` over {extraction['documents']} documents,",
        f"{extraction['readable']} of them readable. Accuracy is exact match per field, with",
        "amounts compared as `Decimal` and no tolerance.",
        "",
        "| Field | Accuracy |",
        "|---|---|",
    ]
    for name, value in extraction["per_field_accuracy"].items():
        lines.append(f"| {name} | {value:.2%} |")

    v1, v2 = extraction["v1_reader_only"], extraction["v2_reader_plus_validators"]
    lines += [
        "",
        "### Reader alone against reader plus validators",
        "",
        "| | Correct records persisted | **Wrong records persisted** | Routed to review | Quarantined |",
        "|---|---|---|---|---|",
        f"| v1 reader only | {v1.get('persisted_correct', 0)} | **{v1.get('persisted_wrong', 0)}** | "
        f"{v1.get('routed_to_review', 0)} | {v1.get('quarantined', 0)} |",
        f"| v2 with validators | {v2.get('persisted_correct', 0)} | **{v2.get('persisted_wrong', 0)}** | "
        f"{v2.get('routed_to_review', 0)} | {v2.get('quarantined', 0)} |",
        "",
        "## Exception detection",
        "",
        f"**Planted defects reaching `cleared`: {current['defects']['reached_cleared']} of "
        f"{current['defects']['planted']}.**",
        "",
        "| Defect | Planted | Caught by its expected check | Flagged by any check | Kept out of cleared |",
        "|---|---|---|---|---|",
    ]
    for code, c in current["defects"]["by_defect"].items():
        lines.append(
            f"| {code} | {c['planted']} | {c.get('caught_by_expected_check', 0)} | "
            f"{c.get('flagged_by_any_check', 0)} | {c.get('kept_out_of_cleared', 0)} |"
        )

    lines += [
        "",
        "| Check | Fired | Fired on its own defects | Defects it owns | Strict recall |",
        "|---|---|---|---|---|",
    ]
    for code, c in current["per_check"].items():
        recall = "n/a" if c["recall_strict"] is None else f"{c['recall_strict']:.2%}"
        lines.append(
            f"| {code} | {c['fired']} | {c['fired_on_its_own_defects']} | "
            f"{c['defects_it_owns']} | {recall} |"
        )

    lines += [
        "",
        "## Routing and false positives",
        "",
        "| | Without materiality floor | Current |",
        "|---|---|---|",
    ]
    rows = [
        (
            "Auto-cleared",
            lambda r: f"{r['routing']['cleared']} ({r['routing']['cleared_share']:.1%})",
        ),
        ("Defects reaching cleared", lambda r: str(r["defects"]["reached_cleared"])),
        (
            "Clean invoices with a failed check",
            lambda r: str(r["clean_invoices"]["with_a_failed_check"]),
        ),
        ("False-positive rate", lambda r: f"{r['clean_invoices']['false_positive_rate']:.2%}"),
        (
            "Clean, routed only because a check abstained",
            lambda r: str(r["clean_invoices"]["routed_only_because_a_check_abstained"]),
        ),
    ]
    for label, fn in rows:
        lines.append(f"| {label} | {fn(floorless)} | {fn(current)} |")

    lines += ["", "Review reasons (current):", "", "| Reason | Documents |", "|---|---|"]
    for reason, count in sorted(current["routing"]["by_reason"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {reason} | {count} |")

    lines += ["", "## Recommendations", "", "| Action | Invoices |", "|---|---|"]
    for action, count in actions.most_common():
        lines.append(f"| {action} | {count} |")

    lines += [
        "",
        "## Manual baseline",
        "",
        "Not yet measured. See [manual_baseline.md](manual_baseline.md). No time-saving claim is",
        "made anywhere until it is.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    started = time.perf_counter()
    truth_invoices = {
        row["id"]: row for row in json.loads((CORPUS / "invoices.json").read_text(encoding="utf-8"))
    }
    vendors = {
        row["id"]: row for row in json.loads((CORPUS / "vendors.json").read_text(encoding="utf-8"))
    }
    truth_rows = {row["invoice_id"]: row for row in json.loads(TRUTH.read_text(encoding="utf-8"))}
    reference = load(CORPUS)

    extraction, outcomes = evaluate_extraction(truth_invoices, vendors)
    _write(RESULTS / "extraction.json", extraction)

    configs = {}
    configured_floor = settings.price_variance_min_pct
    for name, floor in (("without_materiality_floor", Decimal("0")), ("current", configured_floor)):
        settings.price_variance_min_pct = floor
        cases = run_batch(DOCUMENTS, reference, outcomes)
        configs[name] = evaluate_checks(cases, truth_rows)
        configs[name]["price_variance_min_pct"] = str(floor)
        _write(RESULTS / f"checks-{name.replace('_', '-')}.json", configs[name])
    settings.price_variance_min_pct = configured_floor

    toolbox = Toolbox(reference=reference, cases={})
    actions = Counter()
    for case in cases:
        if case.results:
            actions[recommend(case, toolbox)["action"]] += 1
        toolbox.cases[case.document_id] = case
    _write(RESULTS / "recommendations.json", dict(actions))

    REPORT.write_text(_render_report(extraction, configs, actions), encoding="utf-8")
    print(f"evaluated {extraction['documents']} documents in {time.perf_counter() - started:.0f}s")
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
