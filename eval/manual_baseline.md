# Manual baseline

**Status: not yet run.** Until it is, Countersign makes no claim about time saved, anywhere.

This is the only legitimate source of a time comparison in the project. An estimate written
in its place would be the easiest number in the repository to challenge and the hardest to
defend, so the table below stays empty until the exercise has actually been done.

## Protocol

1. Take the 20 documents listed below, a fixed mix of layouts and formats.
2. Open a blank spreadsheet with the columns: invoice number, vendor, date, order reference,
   currency, one row per line (SKU, quantity, unit price, line total), subtotal, tax, total.
3. For each document, start a timer when the file opens and stop it when the row is complete
   and checked once by eye. Record the time for that document before starting the next.
4. Record anything skipped or unreadable, and any value later found to be mistyped.
5. Then run the same 20 through `python -m eval.run` (or the batch on a folder holding only
   them) and record wall-clock time and how many cleared with no human input.

"Done" means keyed, not reconciled. The manual time therefore flatters the manual process:
it excludes checking the order, the delivery, the price history and the tax, which is the
work the checks do.

## Documents

INV-0003, INV-0010, INV-0024, INV-0034, INV-0041, INV-0057, INV-0080, INV-0093, INV-0120,
INV-0155, INV-0201, INV-0226, INV-0240, INV-0270, INV-0308, INV-0336, INV-0365, INV-0394,
INV-0404, INV-0445

## Results

| Document | Seconds to key | Notes |
|---|---|---|
| | | |

| | Manual | Countersign |
|---|---|---|
| Mean seconds per document | not measured | not measured |
| Median seconds per document | not measured | not measured |
| Cleared with no human input | n/a | not measured |
