# ADR-005: A generated corpus with recorded ground truth

**Status:** Accepted · **Date:** 2026-09-20

## Context

Countersign needs invoice documents to develop and evaluate against. Real supplier invoices
are confidential, name real counterparties, and come with no labels saying which ones are
wrong. Public invoice datasets exist for document-AI research but carry no purchase orders
or delivery records, so there is nothing to reconcile against — and reconciliation, not
extraction, is the point.

Without labels there is no evaluation, and without evaluation the accuracy claims are
assertions.

## Decision

Generate the whole corpus from one seed, and record what was planted.

- **Reproducible.** `python -m data.generate` rebuilds vendors, purchase orders, deliveries,
  invoices, ground truth and 500 documents. Regeneration is byte-identical; a test asserts it.
- **Coherent.** A clean invoice bills exactly what was delivered at exactly the ordered
  price. A check that fires on one is unambiguously a false positive — the corpus is never
  the suspect.
- **Labelled.** Roughly 18% of invoices carry exactly one planted defect from eight types,
  written to `data/ground_truth/exceptions.json` with the check expected to catch it. Nothing
  in the pipeline may read that file outside the evaluation harness.
- **Deliberately difficult.** Four PDF layouts that disagree on field labels, date formats
  and money notation; spreadsheet and CSV invoices whose header block defeats a naive table
  read; the same vendor spelled several ways; six image-only pages, two corrupt files and one
  password-protected PDF.
- **Visibly synthetic.** Vendor names are assembled from generic place words, trade words and
  legal suffixes rather than written by hand, so they cannot collide with a real company. The
  buyer is a fictional entity. Every document carries a synthetic-data line.

Two invariants are enforced as tests because the evaluation is worthless without them:

1. A planted defect never breaks the invoice's internal arithmetic by accident — otherwise
   every defect would also look like a tax defect.
2. `PRICE_ABOVE_HISTORY` raises the purchase order price too, so the paperwork is internally
   perfect and only the vendor's price history exposes it. Without this the variance check
   would be credited for catches the three-way match made.

## Consequences

**Good.** Precision and recall are measurable per check. Anyone can reproduce every number.
Adding a defect type is a generator change plus a ground-truth row.

**Costs, stated plainly.** A generator cannot invent the ways real documents are strange. The
corpus is harder than a clean fixture set and easier than reality, and results on it are an
upper bound on real-world performance, not a prediction of it. This is recorded as a
limitation in the README, the dataset card and every evaluation report — not as a footnote.

**Not committed.** The 2.3 MB of documents are regenerable and gitignored; the ground truth
and manifest are small and committed.

## Alternatives considered

**Hand-label real invoices.** Rejected: no lawful access to a real AP inbox, and publishing
derived data from one would be worse.

**Public document-AI invoice datasets.** Rejected as the primary corpus: no purchase orders
or deliveries, so the reconciliation checks have nothing to run against. Worth revisiting as
a second extraction-only test set.

**No corpus; unit tests on handcrafted cases only.** Rejected: it tests the code against the
cases the author already thought of, which is exactly what an evaluation is supposed to
avoid.
