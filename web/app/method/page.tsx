"use client";

import { useJson } from "@/components/data";
import { pct } from "@/components/format";

type Checks = {
  routing: { cleared: number; cleared_share: number };
  defects: { planted: number; reached_cleared: number; recall_any: number };
  clean_invoices: { checked: number; with_a_failed_check: number; false_positive_rate: number };
  per_check: Record<string, { recall_strict: number | null; fired: number; defects_it_owns: number }>;
};

type Evaluation = {
  extraction: {
    documents: number;
    readable: number;
    v1_reader_only: Record<string, number>;
    v2_reader_plus_validators: Record<string, number>;
  };
  "checks-current": Checks;
  "checks-without-materiality-floor": Checks;
};

const REPO = "https://github.com/Niloy-Bhuiyan/countersign";

export default function Method() {
  const { data: e } = useJson<Evaluation>("/data/evaluation.json");
  const now = e?.["checks-current"];
  const before = e?.["checks-without-materiality-floor"];

  return (
    <div className="prose">
      <div className="page-head">
        <div>
          <h1>How it works, and how well</h1>
          <p>
            Countersign turns supplier invoices into decisions a controller can check by hand. A
            language model may read a document. It never decides anything about money.
          </p>
        </div>
      </div>

      <p className="notice">
        All data here is synthetic: 40 vendors, 460 purchase orders and 500 invoice documents
        generated from one seed, with 90 defects planted and recorded. No real company appears
        anywhere. Results on this corpus are an upper bound, not a prediction of performance on real
        invoices.
      </p>

      <h2>Measured results</h2>
      {e && now && before ? (
        <>
          <div className="kpis" style={{ marginTop: 12 }}>
            <div className="panel kpi">
              <div className="label">Planted defects reaching cleared</div>
              <div className="big-number">
                {now.defects.reached_cleared} of {now.defects.planted}
              </div>
              <div className="sub">Target was zero. Why one did is below.</div>
            </div>
            <div className="panel kpi">
              <div className="label">False positives on clean invoices</div>
              <div className="big-number">{pct(now.clean_invoices.false_positive_rate)}</div>
              <div className="sub">
                {pct(before.clean_invoices.false_positive_rate)} before the materiality floor
              </div>
            </div>
            <div className="panel kpi">
              <div className="label">Cleared with no human input</div>
              <div className="big-number">{pct(now.routing.cleared_share)}</div>
              <div className="sub">Still needs an approval to be paid</div>
            </div>
            <div className="panel kpi">
              <div className="label">Wrong records persisted</div>
              <div className="big-number">
                {e.extraction.v1_reader_only.persisted_wrong ?? 0} &rarr;{" "}
                {e.extraction.v2_reader_plus_validators.persisted_wrong ?? 0}
              </div>
              <div className="sub">Reader alone, then with arithmetic validators</div>
            </div>
          </div>
          <table className="plain panel" style={{ marginTop: 4 }}>
            <thead>
              <tr>
                <th>Check</th>
                <th className="num">Defects it owns</th>
                <th className="num">Fired</th>
                <th className="num">Strict recall</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(now.per_check).map(([code, c]) => (
                <tr key={code}>
                  <td className="mono small">{code}</td>
                  <td className="num">{c.defects_it_owns}</td>
                  <td className="num">{c.fired}</td>
                  <td className="num">{pct(c.recall_strict)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="small muted" style={{ marginTop: 6 }}>
            From the committed result files. Full report:{" "}
            <a href={`${REPO}/blob/main/eval/report.md`}>eval/report.md</a>.
          </p>
        </>
      ) : (
        <p className="muted">Loading results…</p>
      )}

      <h2>The pipeline</h2>
      <ol>
        <li>
          <b>Intake.</b> Hash the file; quarantine corrupt, password-protected and image-only documents
          instead of failing the batch.
        </li>
        <li>
          <b>Read.</b> Copy fields as printed. The reader knows supplier vocabulary
          (&ldquo;Invoice No.&rdquo;, &ldquo;Bill Number&rdquo;, &ldquo;Doc #&rdquo;), not layouts. A
          language model can take this step; the published numbers use the offline reader.
        </li>
        <li>
          <b>Parse and validate.</b> Deterministic parsers turn strings into dates and exact decimals.
          Line totals, subtotal and grand total must tie before anything is stored.
        </li>
        <li>
          <b>Check.</b> Three-way match against order and deliveries, price variance against the
          vendor&rsquo;s own history, duplicate detection, exact tax arithmetic.
        </li>
        <li>
          <b>Recommend.</b> A bounded agent with six read-only tools drafts an action. Every sentence
          cites a record; unverifiable sentences are removed.
        </li>
        <li>
          <b>Decide.</b> A person. There is no code path that pays.
        </li>
      </ol>

      <h2>What did not work, and what changed</h2>
      <ul>
        <li>
          <b>The reader silently dropped lines.</b> In two layouts, long descriptions run into the
          next column. Nine records parsed cleanly and were wrong. The subtotal validator now stops
          every one of them.
        </li>
        <li>
          <b>Two companies, one name.</b> &ldquo;Teesta Industries Ltd&rdquo; and &ldquo;Teesta
          Industries Corporation&rdquo; normalise to the same key, by design. Identity is now name
          plus printed tax ID, and a contradiction goes to a person.
        </li>
        <li>
          <b>Statistically unusual is not money at risk.</b> On a tight price history, a 2.6% move
          scored thirteen deviations out. Price variance now also requires a 10% material
          difference. False positives fell from{" "}
          {before ? before.clean_invoices.with_a_failed_check : "58"} to{" "}
          {now ? now.clean_invoices.with_a_failed_check : "0"}; recall did not move.
        </li>
        <li>
          <b>The one defect that cleared.</b> A near-duplicate copied an invoice whose original
          arrived as an image-only scan. With the original unreadable, nothing could see the
          conflict. The next step is re-running duplicate detection over cleared invoices whenever a
          quarantined document is resolved.
        </li>
      </ul>

      <h2>Read the reasoning</h2>
      <p>
        <a href={`${REPO}/blob/main/docs/PRD.md`}>Product requirements</a> ·{" "}
        <a href={`${REPO}/blob/main/docs/architecture.md`}>Architecture</a> ·{" "}
        <a href={`${REPO}/blob/main/docs/security.md`}>Threat model</a> ·{" "}
        <a href={`${REPO}/tree/main/docs/adr`}>Decision records</a> ·{" "}
        <a href={`${REPO}/blob/main/docs/dataset-card.md`}>Dataset card</a>
      </p>
    </div>
  );
}
