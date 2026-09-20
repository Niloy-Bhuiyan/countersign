# ADR-003: Median absolute deviation for price variance

**Status:** Accepted · **Date:** 2026-09-20

## Context

The price-variance check asks whether this invoice's unit price is out of line with what
this vendor has charged for this item before. The obvious implementation is a z-score:
mean and standard deviation over the vendor's price history, flag anything beyond a
threshold.

It has a specific failure that matters here. Mean and standard deviation are both dragged by
the outlier. One inflated price in a short history raises the mean toward itself and inflates
the standard deviation, so the very observation the check exists to catch makes the band wide
enough to contain it. With five to ten observations per vendor and item — which is what this
corpus has — a single 60% overprice can sit inside two standard deviations of a history it
is itself distorting.

## Decision

Robust statistics: **median** as the centre and **median absolute deviation** as the scale.

```
z = 0.6745 * (price - median) / MAD
```

Flag when `|z|` exceeds a configured threshold, default 3.5.

Two supporting decisions:

- **A minimum history of five observations.** Below it the check returns `abstained`, not a
  number. An abstention routes the invoice to human review, so abstaining is not a quiet pass.
- **`MAD == 0` abstains.** A vendor who has charged exactly one price every time produces a
  zero scale, where any deviation is infinitely many MADs. That is an artefact of a short
  stable history, not a finding.

## Consequences

**Good.** The check is not weakened by the thing it is looking for. A controller can
recompute it: sort the vendor's prices, take the middle one, take the middle absolute
difference. Legitimate slow market drift moves the median gradually and does not fire.

**Costs.** Less sensitive than a z-score to a genuine small shift across many observations,
which is a trend question rather than an exception question. The 3.5 threshold and the
5-observation minimum are starting points, not findings — recorded as open questions in
[PRD.md](../PRD.md).

**On the corpus.** 76 of 90 vendor-item pairs clear the minimum, so roughly 16% of the
corpus exercises the abstention path. That is deliberate: a corpus where every pair cleared
the minimum would never test abstention, and one where none did would make the check
meaningless. A test asserts both.

## Alternatives considered

**Mean and standard deviation.** Rejected for the masking problem above.

**Interquartile range.** Comparable robustness. Rejected because it needs more observations
to be stable at this history depth, and MAD is easier to recompute by hand.

**Compare against the catalogue price instead of vendor history.** Rejected: it measures the
wrong thing. Vendors legitimately differ in price; the question is whether *this vendor*
changed.

**A model asked whether the price looks unusual.** Rejected under [ADR-001](ADR-001-llm-boundary.md).
