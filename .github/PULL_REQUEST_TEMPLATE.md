## What this changes

<!-- One or two sentences. What is different after this merges? -->

## Why

<!-- The problem, not the solution. Link an issue or an ADR if there is one. -->

## How it was verified

<!-- The command you ran and what it printed. Not "tested locally". -->

```
```

## Checklist

- [ ] `make check` passes (lint, format, tests, migrations, no schema drift)
- [ ] New behaviour has a test that fails without the change
- [ ] No number in the docs or README that `make eval` does not produce
- [ ] Money stays `Decimal` on any path this touches
- [ ] No new tool reaches the agent that can write

## Anything that got worse

<!-- Tolerances loosened, a check that now abstains more often, a slower path.
     If nothing got worse, say so. -->
