# Contributing

## Setup

```bash
make install     # venv + dependencies
make corpus      # rebuild the synthetic corpus from the committed seed
make check       # lint, format, tests, migrations, schema drift
```

Everything runs offline. If a command needs an API key, that is a bug — the offline provider
is the default and the test suite must never require network access.

## The rules that are not style preferences

These are enforced by tests. A change that breaks one is a defect, not a trade-off.

1. **Money is `Decimal`.** Floats are refused at the money module and at the database type.
   See [ADR-002](docs/adr/ADR-002-decimal-money.md).
2. **The model does not decide anything.** Extraction only. Matching, variance, duplicates
   and tax are deterministic code. See [ADR-001](docs/adr/ADR-001-llm-boundary.md).
3. **No tool that can write reaches the agent.** A test asserts the registry.
4. **State changes go through `states.transition()`.** Never assign to `invoice.state`.
   See [ADR-006](docs/adr/ADR-006-single-state-guard.md).
5. **No number appears in the docs that `make eval` does not produce.** If it has not been
   measured, the doc says so. It does not carry a placeholder.
6. **The ground truth is read only by the evaluation harness.** Nothing in the pipeline may
   open `data/ground_truth/`.

## Adding a check

A check is a module, a test file, a documentation entry and a corpus defect — in that order,
and ideally in separate commits.

1. Specify it in [docs/checks.md](docs/checks.md): the rule, the tolerance, the rationale, a
   worked example, and when it abstains.
2. Implement it in `countersign/checks/`. It returns a `CheckResult` carrying observed,
   expected, tolerance and the records it consulted — never just an outcome.
3. Decide what makes it abstain. A check that cannot abstain will eventually guess.
4. Plant a matching defect in `data/defects.py` with a ground-truth row.
5. Add its evaluation line so precision and recall are reported per check.

## Commits

One logical change per commit. Imperative mood, lower case, under 72 characters, no scope
prefixes, no trailing period, no emoji.

```
add vendor price history aggregation
reject invoice lines whose tax total disagrees with the sum of line taxes
document the three-way match tolerance rules
```

Not `update files`, `fix stuff`, `WIP`, or one commit containing a feature and its tests and
a refactor.

## Tests

A test should fail before the change and pass after it. Prefer a test that pins the
behaviour a controller would notice over one that pins an implementation detail.

Assert the specific exception, not `Exception`. If ingestion has to catch something to
quarantine a file instead of failing a batch, the test names that exception.
