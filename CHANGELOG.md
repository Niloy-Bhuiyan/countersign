# Changelog

Notable changes. Dates are the date the work landed on `main`.

## Unreleased

### Added
- Exact decimal money path with floats refused at the module and database boundaries.
- Invoice state machine with guards: `cleared` requires every check to have passed, and no
  decision state is reachable without a stored human approval.
- Twelve-table schema across procurement, invoice and audit records, with alembic migrations.
- Vendor name normalisation from a committed suffix table.
- Seeded synthetic corpus: 40 vendors, 460 purchase orders, 467 deliveries, 500 invoices,
  90 planted defects across eight types, 500 documents in four PDF layouts plus XLSX and CSV.
- Unreadable-document fixtures: six image-only pages, two corrupt files, one encrypted PDF.
- Product requirements, architecture, and six architecture decision records.

- Intake that quarantines corrupt, encrypted and image-only files instead of failing.
- Offline reader for four PDF layouts, XLSX and CSV; deterministic parsers; arithmetic
  validators that stop wrong-but-plausible extractions before persistence.
- Four checks: three-way match, price variance with a materiality floor, duplicate detection,
  exact tax. Vendor identity by name plus printed tax ID.
- Bounded recommendation agent with six read-only tools and citation verification.
- Evaluation harness and committed results: 1 of 90 planted defects reached `cleared`,
  0.00% false positives on clean invoices, 71.8% auto-cleared.
- Static review console on Vercel: queue, case view, controller view, method page, CSV/XLSX
  export.

### Changed
- Price variance requires a material difference as well as a statistical one (ADR-003).
- A year of closed historical orders added to the corpus; ground truth unchanged.
- Invoices on an order with an unread document are held for review.

### Known
- One planted defect reaches `cleared`: its original is an image-only scan nobody can read.
- The manual baseline has not been run; no time-saving claim is made.
- The API is designed but not built; the console reads exported results.
