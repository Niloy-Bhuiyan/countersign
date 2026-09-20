# Architecture decision records

One file per decision that was not obvious and would be expensive to reverse. Each records
what was actually considered at the time, including the option that was rejected and why.

A decision that had only one plausible option does not get a record here.

| | Decision | Status |
|---|---|---|
| [001](ADR-001-llm-boundary.md) | The language model extracts; deterministic code decides | Accepted |
| [002](ADR-002-decimal-money.md) | Exact decimal money, floats refused at the boundary | Accepted |
| [003](ADR-003-mad-over-standard-deviation.md) | Median absolute deviation for price variance | Accepted |
| [004](ADR-004-committed-normalisation-table.md) | A committed normalisation table, not fuzzy matching | Accepted |
| [005](ADR-005-synthetic-corpus.md) | A generated corpus with recorded ground truth | Accepted |
| [006](ADR-006-single-state-guard.md) | One guarded transition function, not scattered checks | Accepted |
