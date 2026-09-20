"""Build the whole synthetic corpus from one seed.

    python -m data.generate

Records are written to ``data/corpus/`` (regenerable, not committed) and the
ground truth to ``data/ground_truth/`` (small, committed, and the only thing the
evaluation scores against).

Amounts are serialised as strings. Writing them as JSON numbers would route every
amount through a float on the way back in and quietly undo the exactness the rest
of the system is built on.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from data.defects import DEFECT_RATE, EXPECTED_CHECK, plant
from data.invoices import generate_invoices
from data.records import (
    N_PURCHASE_ORDERS,
    N_VENDORS,
    PERIOD_DAYS,
    PERIOD_END,
    generate_deliveries,
    generate_purchase_orders,
    generate_vendors,
)

CORPUS_DIR = Path("data/corpus")
GROUND_TRUTH_DIR = Path("data/ground_truth")


def _encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, default=_encode, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build(seed: int) -> dict:
    rng = random.Random(seed)
    vendors = generate_vendors(rng)
    orders = generate_purchase_orders(rng, vendors)
    deliveries = generate_deliveries(rng, orders)
    invoices = generate_invoices(rng, vendors, orders, deliveries)
    truth = plant(rng, vendors, orders, deliveries, invoices)

    return {
        "vendors": vendors,
        "orders": orders,
        "deliveries": deliveries,
        "invoices": invoices,
        "truth": truth,
    }


def main(seed: int) -> None:
    corpus = build(seed)

    _write(CORPUS_DIR / "vendors.json", [asdict(v) for v in corpus["vendors"]])
    _write(CORPUS_DIR / "purchase_orders.json", [asdict(o) for o in corpus["orders"]])
    _write(CORPUS_DIR / "deliveries.json", [asdict(d) for d in corpus["deliveries"]])
    _write(CORPUS_DIR / "invoices.json", [asdict(i) for i in corpus["invoices"]])

    _write(GROUND_TRUTH_DIR / "exceptions.json", corpus["truth"])
    _write(
        GROUND_TRUTH_DIR / "manifest.json",
        {
            "seed": seed,
            "period_end": PERIOD_END,
            "period_days": PERIOD_DAYS,
            "target_defect_rate": DEFECT_RATE,
            "defect_codes": EXPECTED_CHECK,
            "counts": {
                "vendors": len(corpus["vendors"]),
                "purchase_orders": len(corpus["orders"]),
                "deliveries": len(corpus["deliveries"]),
                "invoices": len(corpus["invoices"]),
                "defects": len(corpus["truth"]),
            },
            "configured": {
                "n_vendors": N_VENDORS,
                "n_purchase_orders": N_PURCHASE_ORDERS,
            },
        },
    )

    counts = {
        "vendors": len(corpus["vendors"]),
        "purchase orders": len(corpus["orders"]),
        "deliveries": len(corpus["deliveries"]),
        "invoices": len(corpus["invoices"]),
        "defects": len(corpus["truth"]),
    }
    for label, value in counts.items():
        print(f"{label:>16}: {value}")
    rate = len(corpus["truth"]) / len(corpus["invoices"]) * 100
    print(f"{'defect rate':>16}: {rate:.1f}%")


if __name__ == "__main__":
    from countersign.settings import settings

    main(settings.corpus_seed)
