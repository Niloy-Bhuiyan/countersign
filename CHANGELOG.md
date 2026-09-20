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

### Notes
- No evaluation numbers are published yet. The harness does not exist, so the README and PRD
  state targets and mark results as not measured.
