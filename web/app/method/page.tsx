"use client";

import Link from "next/link";
import { useJson } from "@/components/api";
import { pct } from "@/components/format";

type Checks = {
  routing: { cleared: number; cleared_share: number };
  defects: { planted: number; reached_cleared: number };
  clean_invoices: { with_a_failed_check: number; false_positive_rate: number };
  per_check: Record<string, { recall_strict: number | null; fired: number; defects_it_owns: number }>;
};
type Evaluation = {
  extraction: { v1_reader_only: Record<string, number>; v2_reader_plus_validators: Record<string, number> };
  "checks-current": Checks;
  "checks-without-materiality-floor": Checks;
};

const REPO = "https://github.com/Niloy-Bhuiyan/countersign";

export default function Method() {
  const { data: e } = useJson<Evaluation>("/data/evaluation.json");
  const now = e?.["checks-current"];
  const before = e?.["checks-without-materiality-floor"];

  return (
    <div className="page">
      <h1 className="page-title">How it works, and how well</h1>
      <p className="lede">
        Countersign reads supplier invoices and checks them the way a controller would, against the
        buyer&rsquo;s own orders and delivery notes. A language model may read a document. Nothing that
        decides anything about money is a model, and nothing pays.
      </p>
      <p className="notice" style={{ marginTop: 18, maxWidth: 760 }}>
        The corpus is synthetic: 40 vendors, 460 purchase orders and 500 invoice documents from one seed,
        90 of them carrying a defect planted on purpose. No real company appears anywhere. Results on it are
        an upper bound, not a forecast of performance on real invoices.
      </p>

      <section className="section">
        <div className="section-head"><h2>Measured</h2><span className="aside"><a href={`${REPO}/blob/main/eval/report.md`}>Full report</a></span></div>
        {now && before && e ? (
          <>
            <div className="figures-row">
              <div><span className="label">Defects reaching cleared</span><div className="big fig">{now.defects.reached_cleared} of {now.defects.planted}</div><div className="sub">Target was zero. Cause below.</div></div>
              <div><span className="label">False positives</span><div className="big fig">{pct(now.clean_invoices.false_positive_rate)}</div><div className="sub">{pct(before.clean_invoices.false_positive_rate)} before the materiality floor</div></div>
              <div><span className="label">Cleared unaided</span><div className="big fig">{pct(now.routing.cleared_share)}</div><div className="sub">Still needs a signature to pay</div></div>
              <div><span className="label">Wrong records stored</span><div className="big fig">{e.extraction.v1_reader_only.persisted_wrong ?? 0} → {e.extraction.v2_reader_plus_validators.persisted_wrong ?? 0}</div><div className="sub">Reader alone, then with validators</div></div>
            </div>
            <table className="sheet" style={{ marginTop: 20 }}>
              <thead><tr><th>Check</th><th className="num">Defects it owns</th><th className="num">Fired</th><th className="num">Strict recall</th></tr></thead>
              <tbody>
                {Object.entries(now.per_check).map(([code, c]) => (
                  <tr key={code}><td className="id">{code}</td><td className="num">{c.defects_it_owns}</td><td className="num">{c.fired}</td><td className="num">{pct(c.recall_strict)}</td></tr>
                ))}
              </tbody>
            </table>
          </>
        ) : <p className="muted">Loading results…</p>}
      </section>

      <div className="two section prose">
        <section>
          <div className="section-head"><h2>The pipeline</h2></div>
          <ol>
            <li><b>Intake.</b> Hash the file. Quarantine corrupt, password-protected and image-only documents instead of failing the batch.</li>
            <li><b>Read.</b> Copy fields as printed, by supplier vocabulary rather than known layouts.</li>
            <li><b>Parse and validate.</b> Exact decimals; line totals, subtotal and total must tie before anything is stored.</li>
            <li><b>Check.</b> Three-way match, price against the vendor&rsquo;s own history, duplicates, exact tax.</li>
            <li><b>Recommend.</b> A bounded agent with six read-only tools drafts an action; every sentence cites a record.</li>
            <li><b>Decide.</b> A named person, on the server, through the same state machine. There is no code path that pays.</li>
          </ol>
          <p>
            Everything in the <Link href="/lab/">invoice lab</Link> and every upload goes through this exact code
            path live, and every decision is recorded on the server in an append-only audit trail.
          </p>
        </section>
        <section>
          <div className="section-head"><h2>What failed, and what changed</h2></div>
          <ul>
            <li><b>Silently dropped lines.</b> Long descriptions ran into the next column and nine records parsed cleanly while wrong. The subtotal validator now stops all nine.</li>
            <li><b>Two companies, one name.</b> Legal-form normalisation merged two real-looking vendors. Identity is now name plus printed tax ID.</li>
            <li><b>Unusual is not material.</b> On a tight history a 2.6% move scored thirteen deviations out. A 10% floor took false positives from {before?.clean_invoices.with_a_failed_check ?? 58} to {now?.clean_invoices.with_a_failed_check ?? 0} with recall unchanged.</li>
            <li><b>The defect that cleared.</b> A near-duplicate of an invoice whose original was an unreadable scan. With the original unreadable nothing could see the conflict, and it is reported rather than tuned away.</li>
          </ul>
        </section>
      </div>

      <section className="section prose">
        <div className="section-head"><h2>The reasoning, in full</h2></div>
        <p>
          <a href={`${REPO}/blob/main/docs/PRD.md`}>Requirements</a> · <a href={`${REPO}/blob/main/docs/architecture.md`}>Architecture</a> ·{" "}
          <a href={`${REPO}/blob/main/docs/security.md`}>Threat model</a> · <a href={`${REPO}/tree/main/docs/adr`}>Decision records</a> ·{" "}
          <a href={`${REPO}/blob/main/docs/dataset-card.md`}>Dataset card</a> · <a href="/api/docs">API reference</a>
        </p>
      </section>
    </div>
  );
}
