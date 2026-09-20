# Countersign — Product Requirements

| | |
|---|---|
| **Status** | In development |
| **Owner** | Nurul Azam Bhuiyan |
| **Last reviewed** | 2026-09-20 |
| **Related** | [architecture.md](architecture.md) · [checks.md](checks.md) · [evaluation.md](evaluation.md) · [adr/](adr/) |

---

## 1. Problem

A manufacturing group's accounts-payable team receives supplier invoices as PDFs and
spreadsheets, from dozens of vendors, in formats that agree with each other about nothing.
The current process is:

1. A clerk reads the document and types its fields into a system.
2. A second person compares it against the purchase order and the delivery record.
3. Someone checks the unit price against what that vendor normally charges.
4. Someone checks the VAT arithmetic.
5. Someone checks the invoice has not already been paid.

Steps 1 and 2 dominate the time. Steps 3 to 5 are the ones most often skipped when the
queue is long, and they are the ones that cost money when skipped.

### What makes this hard rather than tedious

- **The documents disagree.** The same field is `Invoice No.`, `Bill Number` or `Doc #`.
  Dates arrive in four formats. A parser tuned to one vendor breaks on the next.
- **The same supplier has several names.** `Meghna Steel Ltd`, `MEGHNA STEEL LIMITED`,
  `Meghna Steel`. Duplicate detection that compares raw strings misses the duplicate.
- **Being wrong is expensive in both directions.** A missed overbilling is money paid out.
  A false alarm on a correct invoice costs a supplier relationship and a person's afternoon.
- **A wrong automated payment is unrecoverable.** This constrains the design more than any
  accuracy target does.

## 2. Users

| User | What they need | How success looks to them |
|---|---|---|
| **AP reviewer** | To stop typing and start deciding. A queue of invoices that need judgement, each with the evidence already gathered. | Opens a case, sees the finding stated in numbers, decides in under a minute. |
| **Finance controller** | To know what is stuck, what is at risk, and which vendors are drifting on price. | Answers those three questions from one screen without asking anyone. |
| **Internal audit** | To reconstruct why any invoice was paid or held, months later. | Reads the check results, the recommendation and the approval, and needs nothing else. |

## 3. Goals

- **G1** Remove manual data entry for documents the system can read confidently.
- **G2** Run every reconciliation check on every invoice, not just the ones someone had
  time for.
- **G3** State each exception in numbers a controller can act on and verify by hand.
- **G4** Make every decision reconstructable from stored records alone.
- **G5** Make the system's own accuracy measurable, and measure it.

## 4. Non-goals

- **Paying anything.** Countersign produces decisions, never payments. Out of scope
  permanently, not just for v1.
- **Replacing the reviewer.** The target is a better-prepared decision, not an unattended one.
- **OCR of scanned images.** Image-only pages are quarantined. Adding OCR adds an error
  source upstream of every check; it is a later decision, made on evidence.
- **Learning from reviewer corrections.** A model that drifts with feedback is a model whose
  past decisions cannot be reproduced. Not in v1.
- **Multi-currency conversion.** Currency mismatch is detected and escalated, not resolved.
- **ERP write-back.** The integration surface is a documented flat export.

## 5. Requirements

### 5.1 Ingestion

| ID | Requirement | Status |
|---|---|---|
| R1.1 | Accept PDF, XLSX and CSV invoices | Built |
| R1.2 | Hash content on intake; identical bytes are one document | Built |
| R1.3 | Quarantine unreadable, encrypted and image-only files rather than failing the batch | Built (fixtures + tests) |
| R1.4 | Record the file a record came from, permanently | Built (schema) |

### 5.2 Extraction

| ID | Requirement | Status |
|---|---|---|
| R2.1 | Extract to a typed schema, not free text | Planned |
| R2.2 | Validate arithmetic before persisting anything | Planned |
| R2.3 | One bounded retry on validator failure, feeding the failure back | Planned |
| R2.4 | Record provider, model and prompt version on every extraction | Built (schema) |
| R2.5 | Run end to end with no API keys, via an offline provider | Planned |

### 5.3 Checks

| ID | Requirement | Status |
|---|---|---|
| R3.1 | Three-way match: invoice ↔ purchase order ↔ delivery | Planned |
| R3.2 | Price variance against the vendor's own history, robust to outliers | Planned |
| R3.3 | Duplicate and near-duplicate detection | Planned |
| R3.4 | Exact tax arithmetic in decimal | Planned |
| R3.5 | Every result carries observed, expected, tolerance and the records consulted | Built (schema) |
| R3.6 | A check may abstain; abstention routes to review, never to cleared | Built ([states.py](../countersign/states.py)) |

### 5.4 Decision and control

| ID | Requirement | Status |
|---|---|---|
| R4.1 | An invoice reaches `cleared` only when every check passed | Built, tested |
| R4.2 | No decision state is reachable without a stored human approval | Built, tested |
| R4.3 | The agent holds read-only tools; no write tool exists | Planned, test planned |
| R4.4 | Every claim in a recommendation cites a record that exists | Planned |
| R4.5 | Money is exact decimal end to end | Built, tested |

### 5.5 Reporting

| ID | Requirement | Status |
|---|---|---|
| R5.1 | Review queue as the primary screen | Planned |
| R5.2 | Management view: spend, exception rate, value at risk, awaiting decision | Planned |
| R5.3 | Flat CSV/XLSX export shaped for a BI tool | Planned |
| R5.4 | Synthetic-data marker on every screen | Planned |

## 6. Success measures

These are measured by [`make eval`](evaluation.md) from committed result files. **No target
below has been met yet; none has been measured yet.** They are stated in advance so that
tuning toward them afterwards is visible.

| Measure | Target | Why this number |
|---|---|---|
| Per-field extraction accuracy | ≥ 0.95 on header fields | Below this a reviewer re-reads every field and the typing is not removed |
| Planted defects reaching `cleared` | **0** | A missed defect is money out; this is the only zero-tolerance measure |
| False-positive rate on clean invoices | ≤ 0.05 | Above this the queue fills with noise and reviewers start rubber-stamping |
| Documents auto-cleared | ≥ 0.60 | Below this the system has not removed enough work to be worth operating |
| Prompt v1 → v2 improvement | Reported, not targeted | A target here invites tuning the number rather than the extractor |

## 7. Risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Extraction is confidently wrong | A bad record passes every check | Arithmetic validators run before persistence; confidence routes to review |
| Reviewers rubber-stamp recommendations | The approval gate becomes decorative | Recommendations state findings, not verdicts; disagreeing requires a note |
| Tolerances tuned until results look good | The evaluation measures nothing | Targets committed before measurement; failed configurations kept |
| The synthetic corpus is easier than reality | Numbers do not transfer | Stated as a limitation in every report; format variety and unreadable files deliberately included |
| Price history too thin to judge | Variance check fires on noise | Minimum history enforced; the check abstains below it |

## 8. Open questions

1. What price-variance threshold does a controller actually want? 3.5 MAD is a starting
   point, not a finding.
2. Should a near-duplicate block payment or only warn? Currently modelled as blocking.
3. Is a partial delivery followed by a full invoice a defect or normal practice? Currently
   a mismatch.

## 9. Milestones

| | Scope | Status |
|---|---|---|
| **M1** | Schema, state machine, money, synthetic corpus, ground truth | Done |
| **M2** | Ingestion, extraction, validators, offline provider | In progress |
| **M3** | The four checks, each with its own tests | Next |
| **M4** | Agent, citation verification, approval flow | |
| **M5** | Evaluation harness and first measured results | |
| **M6** | API, review queue, dashboard, export | |
| **M7** | Docs, deployment, manual baseline | |
