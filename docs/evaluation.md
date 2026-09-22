# Evaluation

| | |
|---|---|
| **Status** | Harness built and run. Results in [`eval/report.md`](../eval/report.md). |
| **Command** | `make eval` |
| **Last reviewed** | 2026-09-20 |

---

## Why this document exists before the harness

Most of the ways to get a good number are decided before any measurement happens: which set
you score on, what counts as correct, and whether you are allowed to change the system after
seeing the result. Writing those down first is the difference between an evaluation and a
demonstration.

The targets were committed in [PRD.md](PRD.md#6-success-measures) before the first run, so
tuning toward them afterwards would show in the commit history. Three were met and one, zero
planted defects reaching `cleared`, was missed; the PRD records which and why.

## Rules

1. **The ground truth is read only here.** No pipeline module opens `data/ground_truth/`. A
   test asserts it.
2. **Every number in the README and the docs comes from a committed result file.** If
   `make eval` does not produce it, it does not appear. Unmeasured means the section says
   so — it never carries a placeholder figure.
3. **Failed configurations are kept.** A prompt version or tolerance that made things worse
   stays in the repository with its results. Deleting it would make the history a record of
   successes only.
4. **The corpus is not tuned to the result.** If a check misses a planted defect, the fix is
   the check, not the defect.
5. **Limitations travel with the numbers.** Every report repeats that the corpus is synthetic
   and that results on it are an upper bound.

## What gets measured

### 1. Extraction accuracy, per field

**As run:** every readable document is scored against what the generator says it contains,
so the set is all 491 rather than a hand-picked 80. Originally planned: a hand-curated labelled set of at least 80 documents in `eval/labels/`, spanning all four PDF
layouts plus XLSX and CSV.

Reported **per field**, not only in aggregate — a 94% average hides that the grand total is
right 99% of the time and the due date 71%, and those two failures cost completely different
amounts.

| Field | Match rule |
|---|---|
| Invoice number | Exact after whitespace trim |
| Invoice date, due date | Exact as a date, whatever the source format |
| Vendor | Exact after normalisation ([ADR-004](adr/ADR-004-committed-normalisation-table.md)) |
| Currency | Exact |
| Line count | Exact |
| Per line: quantity, unit price, line total | Exact as `Decimal` |
| Subtotal, tax total, grand total | Exact as `Decimal` |

Amounts are compared exactly, with no tolerance. A tolerance here would hide precisely the
error the tax check exists to find.

### 2. The reader alone against the reader with validators

**Changed from the original plan, and why.** The plan compared two prompt versions. The
published numbers use the offline reader, which has no prompt, so the comparison that could
honestly be run is the one that isolates the validators: the same reader's output accepted as
it stands (v1) against the same output checked arithmetically before persistence (v2). Result:
9 wrong records persisted under v1, 0 under v2, with no correct record lost. The prompt
comparison below remains the plan for model-based extraction.

### 2b. Prompt v1 against v2, on the same set (not yet run)

`prompts/v1` is a plain single-prompt extraction. `prompts/v2` is schema-constrained with
arithmetic validators and one bounded retry. Both run over the same labelled set and both
result files are committed.

The delta is the headline engineering result: it says what the validators and the retry were
worth, rather than asserting that they help.

This comparison is also the reason v1 is kept in the repository after v2 replaces it.

### 3. Exception detection, per check

Scored against `data/ground_truth/exceptions.json`: precision, recall and F1 per check code
and overall, plus the confusion matrix.

Two attributions are reported, because they answer different questions:

- **Strict** — did the check named in `expected_check` fire? Tells you whether that check
  works.
- **Any** — was the invoice flagged by any blocking check? Tells you whether the money was
  protected.

A defect may legitimately trip more than one check. Reporting only the strict number would
punish a design where checks overlap on purpose; reporting only the loose one would let one
good check cover for three broken ones.

### 4. Routing outcome

| | |
|---|---|
| Auto-cleared | Share reaching `cleared` with no human input |
| Routed to review | Share reaching `needs_review`, split by reason |
| Quarantined | Documents that could not be read at all |
| **Planted defects reaching `cleared`** | **Must be 0** |

That last row is the only zero-tolerance measure, and it is reported honestly. If it is not
zero, the number is published and the cause explained — not tuned until it looks like zero.

### 5. False positives on clean invoices

The corpus guarantees that a clean invoice ties to the cent and agrees with its purchase
order and delivery. Any check firing on one is a false positive with no ambiguity about
whether the data was at fault.

Reported as a rate and as a list, because the individual cases are more informative than the
rate.

### 6. The manual baseline — measured, not estimated

`eval/manual_baseline.md` will record an actual timed exercise:

1. Hand-key 20 invoices from the corpus into a blank spreadsheet, timing each one
   individually.
2. Record every time, the mean, the median, and the method — including what counted as
   "done" and what was skipped.
3. Run the same 20 through the pipeline; record wall-clock time and how many cleared without
   human input.

This is the **only** legitimate source of a time claim in this project.

There will be no "reduces processing time by 80%" anywhere. Until the exercise has been run,
this section says the measurement is pending. An estimate dressed as a measurement is the
single easiest thing to catch in an interview, and the hardest to recover from.

## Output

```
eval/
  run.py                                  the harness; the only reader of the ground truth
  results/
    extraction.json                       per-field accuracy, reader alone vs with validators
    checks-current.json                   detection, routing, false positives
    checks-without-materiality-floor.json the configuration it replaced, kept
    recommendations.json                  the agent's action mix
  manual_baseline.md                      protocol; results not yet recorded
  report.md                               generated; what the README quotes
```

`make eval` regenerates everything under `results/` and rewrites `report.md`. Raw result
files are committed so a reader can recompute any figure without running anything.

## What this evaluation cannot tell you

- **Whether it works on real invoices.** It measures performance on a generated corpus whose
  difficulty was chosen by the same person who wrote the checks. See the limitations in the
  [dataset card](dataset-card.md#limitations).
- **Whether the tolerances are right.** It measures the checks against defects planted to be
  outside those tolerances. Whether 2% is the right price tolerance for a real business is a
  question for a controller, and it is recorded as open in [PRD.md](PRD.md#8-open-questions).
- **Whether reviewers make better decisions.** That needs people, and this project has none.
