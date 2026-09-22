"use client";

import Link from "next/link";
import { useJson } from "@/components/api";
import { CHECKS } from "@/components/explain";
import { pct } from "@/components/format";
import { Tip } from "@/components/ui";

type Checks = {
  routing: { cleared: number; cleared_share: number };
  defects: { planted: number; reached_cleared: number };
  clean_invoices: { with_a_failed_check: number; false_positive_rate: number; checked: number };
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
  const caught = now ? now.defects.planted - now.defects.reached_cleared : null;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>How accurate is it?</h1>
          <p>We planted mistakes on purpose, recorded which ones, and counted what it caught.</p>
        </div>
      </div>

      <div className="grid-4">
        <div className="card stat">
          <div className="stat-top">Mistakes caught
            <Tip>Out of {now?.defects.planted ?? 90} planted mistakes (overcharges, duplicates, wrong VAT and so on), this many were stopped before they could be paid.</Tip>
          </div>
          <div className="stat-value">{caught ?? "…"}<small>of {now?.defects.planted ?? "…"}</small></div>
        </div>
        <div className="card stat">
          <div className="stat-top">False alarms
            <Tip>How often a correct invoice was wrongly flagged. Before a fix, this was {pct(before?.clean_invoices.false_positive_rate)}.</Tip>
          </div>
          <div className="stat-value">{now ? pct(now.clean_invoices.false_positive_rate) : "…"}</div>
        </div>
        <div className="card stat">
          <div className="stat-top">Passed automatically</div>
          <div className="stat-value">{now ? pct(now.routing.cleared_share, 0) : "…"}</div>
        </div>
        <div className="card stat">
          <div className="stat-top">Misread and saved
            <Tip>How many invoices were read wrongly and saved anyway. Adding a step that checks the sums add up brought it to zero.</Tip>
          </div>
          <div className="stat-value">{e ? `${e.extraction.v1_reader_only.persisted_wrong ?? 0} → ${e.extraction.v2_reader_plus_validators.persisted_wrong ?? 0}` : "…"}</div>
        </div>
      </div>

      <section className="card section">
        <div className="card-head"><h2>Each check on its own</h2></div>
        <div className="table-wrap">
          <table className="t">
            <thead><tr><th>Check</th><th className="r">Planted</th><th className="r">Caught</th></tr></thead>
            <tbody>
              {now && Object.entries(now.per_check).map(([code, c]) => (
                <tr key={code}>
                  <td>{CHECKS[code]?.name ?? code}</td>
                  <td className="r">{c.defects_it_owns}</td>
                  <td className="r">{pct(c.recall_strict, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid-2 section">
        <section className="card card-pad prose">
          <h2 style={{ fontSize: 17 }}>What we fixed</h2>
          <ul>
            <li><b>Skipped lines.</b> Now the lines must add up to the subtotal, or the invoice is stopped.</li>
            <li><b>Look-alike names.</b> Suppliers are now matched by tax ID too.</li>
            <li><b>Price false alarms.</b> A price must now be unusual <i>and</i> 10% higher: {before?.clean_invoices.with_a_failed_check ?? 58} → {now?.clean_invoices.with_a_failed_check ?? 0}.</li>
          </ul>
        </section>
        <section className="card card-pad prose">
          <h2 style={{ fontSize: 17, display: "flex", gap: 10, alignItems: "center" }}><span className="dot dot-warn" aria-hidden />The one it missed</h2>
          <p style={{ marginTop: 8 }}>
            A bill sent twice under a new number. The original was an unreadable scan, so there was nothing to compare
            against. It still needed a signature, so it wasn&rsquo;t paid.
          </p>
        </section>
      </div>

      <section className="section">
        <div className="callout">
          <div>
            <h4>The data is made up</h4>
            <p>
              So these numbers are a best case. Full method in the <a href={`${REPO}/blob/main/eval/report.md`}>evaluation
              report</a>, or <Link href="/lab/">test it yourself</Link>.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
