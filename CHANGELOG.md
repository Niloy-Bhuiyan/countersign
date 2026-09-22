# Changelog

Notable changes. Dates are the date the work landed on `main`.

## Unreleased

### Fixed — 2026-09-22
- Resubmitting a lab invoice returned 500 on the live store, which refuses overwrites; it no
  longer rewrites the stored original. The in-memory store now refuses overwrites too, so
  tests catch this class of bug.
- A Windows-1252 CSV, a damaged spreadsheet, or a PDF that crashed the parser returned 500;
  each is now read or quarantined.

### Security — 2026-09-22
- Content Security Policy, framing, permissions and sandbox headers; CSV formula neutralising;
  limits on note length, upload reads and documents per workspace; storage failures reported
  as 409 or 503 with a readable message.

### Added — live system
- FastAPI function on Vercel running the evaluated pipeline on uploads and lab invoices.
- Invoice lab: raises an order at the vendor's usual prices, records the delivery, renders
  the supplier's PDF and reads it back; each tamper is caught by the check it targets.
- Server-side decisions through the state machine, append-only in a private Blob store,
  with per-reviewer workspaces and a CSV audit trail (ADR-007).
- Console redesigned as an audit working paper: ledger beside the open case, price-history
  evidence charts, lines against order and deliveries, and a countersignature on decision.


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
