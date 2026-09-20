# ADR-001: The language model extracts; deterministic code decides

**Status:** Accepted · **Date:** 2026-09-20

## Context

Countersign has to turn supplier documents into decisions about money. A language model is
the only practical tool for the first half of that: invoice layouts vary per vendor, field
labels disagree, and no rule set survives contact with the fortieth supplier.

The temptation is to let the same model do the second half — hand it the invoice, the
purchase order and the delivery note, and ask whether they agree. It reads well in a demo.

Three things make it the wrong choice here:

1. **A finding has to be recomputable.** A controller told "this invoice is 6.2% over the
   ordered price" will check that number. If the number came from a model, it cannot be
   reproduced, and if it is wrong there is no place to look.
2. **The failure is silent and asymmetric.** A model that quietly misreads a quantity
   produces a confident pass. Nothing downstream can tell that apart from a real pass.
3. **Audit needs a rule, not a rationale.** "Why was this held?" must be answerable with a
   rule identifier, observed and expected values, and a tolerance — not a paragraph.

## Decision

The model's responsibility ends at producing a typed record. Everything after that is
deterministic code operating on persisted data.

- Extraction: LLM, schema-constrained, arithmetic-validated, one bounded retry.
- Matching, variance, duplicates, tax: pandas, NumPy and `Decimal`. No model.
- Recommendation: an agent reasoning *about* check results it cannot recompute or alter.
- Payment: a human.

The agent's tool catalogue is read-only. Not permissioned — absent, with a test asserting
the registry contains no mutating operation.

## Consequences

**Good.** Every check result can be recomputed from stored records years later. Tolerances
are configuration a controller can argue with. The model can be swapped, or fail entirely,
without changing any finding. Evaluation can score extraction and checking separately, so a
bad number has one owner.

**Costs.** More code than a single prompt. Each check has to be specified precisely, which
surfaces questions nobody had answered (is a partial delivery followed by a full invoice a
defect?). Genuinely ambiguous line matching falls back to description similarity with a
stated threshold, which is the one place a judgement call is encoded as a number.

## Alternatives considered

**Model does everything, with the records in context.** Rejected: unauditable, and its
mistakes are invisible rather than loud.

**Model proposes checks, code executes them.** Rejected: the check set is small, stable and
domain-defined. Generating it adds a failure mode and removes the ability to state, in
advance, exactly which checks every invoice receives.

**Model as a second opinion after the checks.** This is close to what was built — the agent
does review the findings. The distinction kept is that it can never overturn one.
