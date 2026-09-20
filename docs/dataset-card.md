# Dataset card — Countersign synthetic corpus

| | |
|---|---|
| **Version** | Seed `20260920` |
| **Built by** | `python -m data.generate` |
| **Committed** | Ground truth and manifest only. The 2.3 MB of documents are regenerable and ignored. |
| **Licence** | MIT, with the code |

---

## In one line

A fully synthetic accounts-payable corpus: procurement records, invoice documents in six
formats, and a recorded list of exactly which invoices are wrong and why.

## This data is not real

No real vendor, company, transaction or document appears anywhere in it.

- **Vendor names are assembled**, not written. Each is a draw from a list of generic place
  words, a list of trade words and a list of legal suffixes. This is deliberate: a
  hand-written list of plausible Bangladeshi supplier names would eventually collide with a
  real company.
- **The buyer is fictional** — "Meridian Industrial Group Ltd". An earlier draft used a real
  group's name and it was removed: five hundred fabricated invoices naming a real company as
  counterparty are documents that could be mistaken for records of a real trading relationship.
- **Prices are order-of-magnitude plausible** for cement, steel, textile, jute, packaging,
  spares and freight in BDT. They are not market data and must not be read as such.
- **Every document carries a synthetic-data line** in its footer.

## Contents

| | Count |
|---|---|
| Vendors | 40 |
| Item catalogue | 27 SKUs across 9 categories |
| Purchase orders | 460 |
| Deliveries | 467 (some orders split across two shipments; 38 orders never delivered) |
| Invoices | 500 |
| Invoices carrying a defect | 90 (18.0%) |
| Documents | 500 — 394 PDF, 71 XLSX, 35 CSV |
| Period | 425 days ending 2026-09-01 |

## Structure

Each vendor supplies a small fixed set of SKUs from one category and is ordered from
repeatedly, so every vendor-item pair accumulates price history. 76 of 90 pairs reach the
five-observation minimum the variance check requires; the remaining 14 exercise its
abstention path. Both facts are asserted by a test, because a corpus where every pair cleared
the minimum would never test abstention and one where none did would make the check
meaningless.

Prices drift slowly over the period and carry ±1.5% jitter, so a genuine market move does not
look like a defect.

## Planted defects

Roughly 18% of invoices carry **exactly one** defect. `data/ground_truth/exceptions.json`
records the invoice, the defect code, the check expected to catch it first, and a
human-readable detail.

| Code | What is wrong | Expected check |
|---|---|---|
| `QTY_OVER_DELIVERY` | Billed quantity exceeds what was delivered | `THREE_WAY_MATCH` |
| `PRICE_ABOVE_PO` | Unit price above the ordered price beyond tolerance | `THREE_WAY_MATCH` |
| `PRICE_ABOVE_HISTORY` | Price far above this vendor's own history for the item | `PRICE_VARIANCE` |
| `DUPLICATE_EXACT` | The same invoice resubmitted unchanged | `DUPLICATE_INVOICE` |
| `DUPLICATE_NEAR` | Same order and total under a different invoice number | `DUPLICATE_INVOICE` |
| `TAX_MISMATCH` | Stated tax disagrees with the sum of line taxes | `TAX_ARITHMETIC` |
| `NO_DELIVERY` | Billed against an order with no delivery recorded | `THREE_WAY_MATCH` |
| `CURRENCY_MISMATCH` | Billed in a different currency from the order | `THREE_WAY_MATCH` |

Two properties make these labels usable:

1. **A defect never breaks the invoice's arithmetic by accident.** Raising a quantity
   recomputes the line total, subtotal and tax, so the invoice still adds up and only the
   comparison against the delivery fails. Otherwise every defect would also read as a tax
   defect.
2. **`PRICE_ABOVE_HISTORY` raises the purchase order price too.** The invoice then agrees
   with its own paperwork exactly, and only the vendor's price history exposes it. Without
   this the variance check would be credited for catches the three-way match made.

`expected_check` names the check that should catch a defect *first*. A defect may
legitimately trip more than one; the evaluation reports both per-check attribution and
whether the invoice was flagged at all. Contorting the corpus so exactly one check fires
would be tuning the data to the answer.

## Document difficulty

Extraction is only a real problem if the documents disagree with each other.

- **Four PDF layouts.** Field labels differ (`Invoice No.` / `Bill Number` / `Doc #` /
  `INV NO`), dates differ (`15 Mar 2026` / `2026-03-15` / `15/03/2026` / `Mar 15, 2026`),
  money differs (`BDT 1,234.56` / `1,234.56 BDT` / `Tk. 1,234.56` / `1,234.56`), and the tax
  column is present in two layouts and absent in two. Layout is assigned per vendor, because
  a supplier's invoices look like each other — so a parser that overfits to one vendor fails
  on a predictable subset rather than at random.
- **Spreadsheets are not tables.** A header block sits above the lines and the totals sit
  below them in the last two columns, with blank rows between. `pd.read_excel` returns header
  text, not line items.
- **The same vendor is spelled several ways** across documents: case, spacing, `Ltd` against
  `Limited`, trailing punctuation, `&` against `and`. A test checks that all 40 vendors'
  variants normalise to one key.

## Unreadable files

Nine documents cannot be read at all: six image-only pages with no text layer, two corrupt
files, one password-protected PDF. They exist so intake has to quarantine rather than crash,
and so the routing report has a category for documents nobody could read.

**Unreadable files are only ever given to clean invoices.** A defect hidden inside a file
nothing could open would depress recall for a reason that has nothing to do with the checks.
A test asserts it.

## Reproducibility

`python -m data.generate` rebuilds everything from the seed in
`data/ground_truth/manifest.json`. Regeneration is byte-identical, and a test asserts that
two builds at the same seed produce the same invoice ids, numbers and ground truth.

Documents are emitted from a separate generator stream, so adding or removing a rendering
step cannot shift the records or the labels.

Amounts serialise as JSON **strings**. Writing them as numbers would route every amount
through a float on the way back in and quietly undo the exactness the rest of the system is
built on.

## Limitations

State these wherever results from this corpus are quoted.

- **A generator cannot invent the ways real documents are strange.** Handwritten annotations,
  stapled continuation sheets, a supplier who changes format mid-year, an invoice that
  references three purchase orders — none of that is here.
- **Results on this corpus are an upper bound**, not a prediction of real-world performance.
- **Single currency pair.** `CURRENCY_MISMATCH` is detected, never resolved.
- **No true scans.** The image-only pages are vector blocks with no text layer. They test the
  quarantine path, not OCR.
- **One defect per invoice.** Real invoices carry several problems at once, and interacting
  defects are not represented.
- **The defect rate is a design choice.** 18% is far above what a real AP inbox sees, chosen
  so per-check precision and recall have enough positives to be meaningful. Any rate-dependent
  measure must be read with that in mind.

## Intended use

Developing and evaluating Countersign. It is not a benchmark for anyone else's system, and
it is not a description of any real procurement operation.
