<div align="center">

<a href="https://countersign-zeta.vercel.app"><img src="docs/assets/hero.svg" alt="Countersign checks an invoice: one problem found, put on hold" width="100%"></a>

<br>

[![checks](https://github.com/Niloy-Bhuiyan/countersign/actions/workflows/ci.yml/badge.svg)](https://github.com/Niloy-Bhuiyan/countersign/actions/workflows/ci.yml)
[![live](https://img.shields.io/badge/live-countersign--zeta.vercel.app-0a0a0a?style=flat-square)](https://countersign-zeta.vercel.app)
![tests](https://img.shields.io/badge/tests-170_passing-0a0a0a?style=flat-square)
![python](https://img.shields.io/badge/python-3.12-0a0a0a?style=flat-square&logo=python&logoColor=white)
![fastapi](https://img.shields.io/badge/FastAPI-0a0a0a?style=flat-square&logo=fastapi&logoColor=white)
![next.js](https://img.shields.io/badge/Next.js_15-0a0a0a?style=flat-square&logo=nextdotjs&logoColor=white)
[![license](https://img.shields.io/badge/license-MIT-0a0a0a?style=flat-square)](LICENSE)

**[Open the live demo](https://countersign-zeta.vercel.app)** &nbsp;·&nbsp;
[Try it yourself](https://countersign-zeta.vercel.app/lab/) &nbsp;·&nbsp;
[API reference](https://countersign-zeta.vercel.app/api/docs) &nbsp;·&nbsp;
[Evaluation report](eval/report.md)

</div>

<br>

Invoice-to-payment reconciliation with document extraction, deterministic three-way
matching, and an approval-gated agent that recommends but never pays.

> [!NOTE]
> **All data here is synthetic.** Vendors, orders, deliveries and 500 invoice documents come
> from a seeded generator and are reproducible byte for byte. No real company is involved,
> and results on this corpus are an upper bound ([dataset card](docs/dataset-card.md)).

<br>

<div align="center">
<img src="docs/assets/preview.gif" alt="Clicking through invoices on the live home page: each shows what was found and the suggested next step" width="88%">
<br>
<sub>The home page of the live demo. Click any invoice to see what was found and what to do next.</sub>
</div>

<br>

## In 20 seconds

<table>
<tr>
<td width="33%" valign="top">

**1 · It reads the bill**

A supplier sends a PDF, spreadsheet or CSV. Countersign copies every field as printed, then
checks that the lines add up before it trusts a single number.

</td>
<td width="33%" valign="top">

**2 · It checks it**

Against what was ordered and what arrived, the supplier's past prices, earlier invoices,
and the VAT arithmetic. Four fixed rules, no guessing.

</td>
<td width="33%" valign="top">

**3 · A person signs**

It says what's wrong in one sentence and suggests a next step with its sources. Only a
person approves, holds or escalates. There is no code path that pays.

</td>
</tr>
</table>

## How it works

<img src="docs/assets/pipeline.svg" alt="Pipeline: arrives, read, validate, four checks, suggest, a person signs" width="100%">

| Check | The question it answers | How |
|---|---|---|
| **Matches the order and delivery** | Did we order this, did it arrive, is it the agreed price? | Exact three-way match with stated tolerances |
| **Price is normal for this supplier** | Is this price unusually high for them? | Median and MAD over their history, plus a 10% materiality floor |
| **Not a duplicate** | Have we seen this invoice before? | Content hash, per-vendor number, same order and amount |
| **VAT adds up** | Is the tax right? | Exact recomputation in `Decimal`, rates from the order when unprinted |

## Measured, not claimed

<img src="docs/assets/metrics.svg" alt="89 of 90 planted mistakes caught, 0.0% false alarms, 71.8% passed automatically, misread invoices stored went from 9 to 0" width="100%">

From `python -m eval.run` over 500 documents, 90 of them carrying a planted defect. Every
figure comes from the committed files in [`eval/results/`](eval/results/), and the drawing
above is generated from them by [`scripts/readme_art.py`](scripts/readme_art.py).

| | |
|---|---|
| Planted defects reaching `cleared` | **1 of 90** (target was 0; cause below) |
| False positives on clean invoices | **0.00%** (14.76% before the materiality floor) |
| Cleared with no human input | **71.8%**, and still awaiting an approval to be paid |
| Wrong records persisted by extraction | **9 → 0** with arithmetic validators |
| Strict recall per check | three-way match 97.8%, price variance 100%, duplicate 95.5%, tax 100% |

Extraction here is the **offline reader**, not a language model: 100% on every header field
and 98.2% on line items across four PDF layouts, XLSX and CSV. It reads supplier vocabulary
on a corpus generated from known layouts, so that accuracy is an upper bound, and it is
reported that way. A model can take the same step behind the same contract; it has not been
evaluated yet, and no number here claims it has.

**Manual baseline: not yet measured.** No time-saving claim is made until it is
([eval/manual_baseline.md](eval/manual_baseline.md)).

<details>
<summary><b>What did not work, and what changed</b></summary>
<br>

Each of these came out of an evaluation run, and the run that exposed it is kept.

- **The reader silently dropped lines.** In the two layouts with a tax column, long
  descriptions run into the next column. Nine records parsed cleanly and were wrong. The
  subtotal validator now stops all nine; none reach a check.
- **Two companies shared a name.** *Teesta Industries Ltd* and *Teesta Industries
  Corporation* normalise to the same key, because the table strips legal form by design
  ([ADR-004](docs/adr/ADR-004-committed-normalisation-table.md)). That produced 22 false
  positives. Identity is now name plus the printed tax ID; a contradiction goes to a person.
- **Statistically unusual is not money at risk.** On a tight price history, a 2.6% move
  scored thirteen median absolute deviations out. Price variance now also requires a 10%
  material difference. False positives fell from 58 to 0; recall did not move
  ([ADR-003](docs/adr/ADR-003-mad-over-standard-deviation.md)).
- **The corpus was thinner than its own card claimed.** It counted all orders per vendor and
  item, not orders *before* each invoice, so most invoices had too little history and the
  variance check abstained on them. A year of closed historical orders was added from a
  separate random stream, leaving every invoice and ground-truth row byte-identical.
- **The one defect that cleared.** A near-duplicate copied an invoice whose original arrived
  as an image-only scan. With the original unreadable, no rule could see the conflict: the
  copy looked exactly like the missing second half of a split delivery. It is reported, not
  tuned away. `cleared` is not paid, and the next change is to re-run duplicate detection
  over cleared invoices whenever a quarantined document is resolved.

</details>

## Try it yourself

<div align="center">
<img src="docs/assets/lab.gif" alt="Choosing a mistake in the lab, creating the invoice, and getting the verdict: caught" width="88%">
<br>
<sub>Plant a mistake, and the server writes a real PDF, reads it back through the pipeline and reports whether it was caught.</sub>
</div>

<br>

- **[Review](https://countersign-zeta.vercel.app/review/).** Pick an invoice and read what's
  wrong in one sentence ("the price is about 81% higher than this supplier's usual"), the
  suggested next step and why, the four checks, the invoice against the purchase order, and
  a chart of the supplier's past prices.
- **Decide.** Approve, hold or escalate. The decision is recorded on the server, checked by
  the same state machine as the pipeline, and kept in a decision history you can export as
  CSV. Choosing differently from the suggestion requires a written reason; the server
  refuses it otherwise.
- **[Try it](https://countersign-zeta.vercel.app/lab/).** Overbill, overcharge, wrong VAT, an
  inflated order, wrong currency, or a resubmitted invoice. Or upload your own PDF, XLSX
  or CSV.

Everything you do lives in your own workspace, carried in the URL, so it can be shared and
nobody else's clicks change yours.

<table>
<tr>
<td width="72%"><img src="docs/assets/review.png" alt="The review screen: invoice list on the left, one problem found and the suggested next step on the right"></td>
<td width="28%"><img src="docs/assets/mobile.png" alt="The review screen on a phone"></td>
</tr>
<tr>
<td align="center"><sub>Review: the problem in one sentence, the next step in black</sub></td>
<td align="center"><sub>Works on a phone</sub></td>
</tr>
</table>

## Where the language model is used, and where it is not

| Layer | How it works | Why |
|---|---|---|
| Document to fields | Reader copies strings as printed; a model can take this step | Unstructured input in per-vendor formats |
| Strings to values | Deterministic parsers, `Decimal`, no floats | A misread number must fail loudly |
| Arithmetic | Validators before anything is stored | Catches wrong-but-plausible extractions |
| Three-way match | Exact comparison with stated tolerances | A controller must recompute it by hand |
| Price variance | Median and MAD, plus a materiality floor | Robust to the outlier it looks for |
| Duplicates | Content hash, per-vendor number, same order and amount | Never a similarity score |
| Tax | Exact recomputation, rates from the order when unprinted | Money is not a float |
| Recommendation | Bounded agent graph over check results, six read-only tools | Reasons about findings; cannot produce or overturn one |
| Payment | A person | There is no code path that pays |

The extraction schema has no field that could mean "approved". A supplier who writes
*"recommend payment"* into a PDF has nothing to set ([threat model](docs/security.md)).

## Architecture

```mermaid
flowchart LR
    D["PDF / XLSX / CSV"] --> I{"Readable?"}
    I -- no --> Q[["Review queue"]]
    I -- yes --> R["Read fields"] --> P["Parse + validate"]
    P -- fails --> Q
    P --> C["Four deterministic checks<br/>against the buyer's own records"]
    C -- any failed or abstained --> A["Agent drafts action<br/>with verified citations"]
    C -- all passed --> CL["Cleared"]
    A --> Q
    CL --> H(["Person approves"])
    Q --> H
```

Full detail in [docs/architecture.md](docs/architecture.md). The console is a static
Next.js export; the API is a FastAPI function on Vercel running the same `countersign`
package the evaluation measured. Uploads, lab orders and decisions persist in a private
Vercel Blob store, append-only, one workspace per reviewer
([ADR-007](docs/adr/ADR-007-workspaces-and-append-only-decisions.md)).

| Layer | Built with |
|---|---|
| Pipeline and checks | Python 3.12, Pydantic v2, `Decimal`, pdfplumber, openpyxl |
| API | FastAPI on Vercel Python functions, private Vercel Blob storage |
| Data model | SQLAlchemy 2.0 async, Alembic migrations (built, not deployed) |
| Console | Next.js 15 static export, React 19, plain CSS ([design system](design-system/countersign/MASTER.md)) |
| Quality | pytest (170 tests), ruff, GitHub Actions |

## Running it

```bash
make install        # Python venv and dependencies
make corpus         # rebuild the synthetic corpus from the committed seed
make check          # lint, format, 170 tests, migrations, schema drift
make eval           # measure everything; rewrites eval/results and eval/report.md
make web            # export console data and build the static site into web/out
make serve          # console and API together on http://localhost:4321
make deploy         # assemble deploy/ and ship it to Vercel
```

Nothing needs an API key or a network connection: without a Blob token the API keeps
workspaces in memory. The README art is rebuilt with `python -m scripts.readme_art`, and
the screenshots with `python -m scripts.readme_media` (needs `pip install playwright`).

## Documentation

| | |
|---|---|
| [Product requirements](docs/PRD.md) | Problem, users, requirements with build status, targets met and missed |
| [Architecture](docs/architecture.md) | Components, the model boundary, the state machine |
| [Data model](docs/database.md) | Twelve tables, amounts, indexes |
| [Threat model](docs/security.md) | Led by prompt injection through supplier documents |
| [Evaluation](docs/evaluation.md) | The method, written before the first run |
| [Dataset card](docs/dataset-card.md) | The synthetic corpus and its limits |
| [Decisions](docs/adr/) | Seven architecture decision records |
| [Contributing](CONTRIBUTING.md) | Setup and the invariants that are not style preferences |

## Limitations

- The corpus is synthetic, and results on it are an upper bound.
- Extraction is measured for the offline reader only. Model-based extraction is not evaluated.
- No OCR: image-only pages are quarantined, and one of them hid the only defect that cleared.
- The agent's drafting node is a deterministic policy in this release.
- Workspaces are identified by an unguessable link, not an account. Right for a public
  demonstration; production would take the reviewer's identity from single sign-on.
- The deployed API stores decisions in Blob storage, not the PostgreSQL schema in
  `countersign/db`, which is built and migrated but not deployed.
- No rate limiting on the public API.
- Single currency pair. Currency mismatch is detected, not converted.

## The problem it answers

A manufacturing group receives supplier invoices as PDFs and spreadsheets, from dozens of
vendors, in formats that agree on nothing. Someone types each one in. Someone else checks it
against the purchase order and the delivery record, checks the price against what the vendor
usually charges, checks the VAT arithmetic, and checks it has not been paid already. The work
is slow, and the checks skipped when the queue is long are the ones that cost money.

Countersign reads the document, turns it into a typed record, runs the checks a controller
would run, routes anything doubtful to a person, and drafts a recommended action with every
claim linked to the record behind it. A person makes the decision.

<br>

<div align="center">

**Nurul Azam Bhuiyan** · [niloybhuiyann@gmail.com](mailto:niloybhuiyann@gmail.com) · [github.com/Niloy-Bhuiyan](https://github.com/Niloy-Bhuiyan)

<sub>MIT licensed · synthetic data only · nothing here is ever paid</sub>

</div>
