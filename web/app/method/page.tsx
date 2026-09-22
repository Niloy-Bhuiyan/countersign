"use client";

import { AlertTriangle, BadgeCheck, CheckCircle2, ShieldCheck, Target } from "lucide-react";
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
          <p>
            We tested Countersign the honest way: we deliberately planted mistakes in the demo invoices, recorded exactly
            which ones, and measured how many it caught. Here are the results, including what went wrong.
          </p>
        </div>
      </div>

      <div className="grid-4">
        <div className="card stat">
          <div className="stat-top"><span className="stat-icon tone-ok"><Target size={18} aria-hidden /></span>Mistakes caught
            <Tip>Out of {now?.defects.planted ?? 90} planted mistakes (overcharges, duplicates, wrong VAT and so on), this many were stopped before they could be paid.</Tip>
          </div>
          <div className="stat-value">{caught ?? "…"}<small>of {now?.defects.planted ?? "…"}</small></div>
          <div className="stat-meaning">Planted mistakes stopped before payment.</div>
        </div>
        <div className="card stat">
          <div className="stat-top"><span className="stat-icon tone-ok"><BadgeCheck size={18} aria-hidden /></span>False alarms
            <Tip>How often a correct invoice was wrongly flagged. Before a fix, this was {pct(before?.clean_invoices.false_positive_rate)}.</Tip>
          </div>
          <div className="stat-value">{now ? pct(now.clean_invoices.false_positive_rate) : "…"}</div>
          <div className="stat-meaning">Correct invoices wrongly flagged.</div>
        </div>
        <div className="card stat">
          <div className="stat-top"><span className="stat-icon tone-primary"><CheckCircle2 size={18} aria-hidden /></span>Handled automatically</div>
          <div className="stat-value">{now ? pct(now.routing.cleared_share, 0) : "…"}</div>
          <div className="stat-meaning">Invoices that needed no investigation, only a sign-off.</div>
        </div>
        <div className="card stat">
          <div className="stat-top"><span className="stat-icon tone-primary"><ShieldCheck size={18} aria-hidden /></span>Misread invoices stored
            <Tip>How many invoices were read wrongly and saved anyway. Adding a step that checks the sums add up brought it to zero.</Tip>
          </div>
          <div className="stat-value">{e ? `${e.extraction.v1_reader_only.persisted_wrong ?? 0} → ${e.extraction.v2_reader_plus_validators.persisted_wrong ?? 0}` : "…"}</div>
          <div className="stat-meaning">Before and after checking the sums.</div>
        </div>
      </div>

      <section className="card section">
        <div className="card-head"><div><h2>Each check on its own</h2><p className="card-sub">Of the planted mistakes each check was meant to catch, how many it caught.</p></div></div>
        <div className="table-wrap">
          <table className="t">
            <thead><tr><th>Check</th><th className="r">Mistakes meant for it</th><th className="r">Caught</th></tr></thead>
            <tbody>
              {now && Object.entries(now.per_check).map(([code, c]) => (
                <tr key={code}>
                  <td><b>{CHECKS[code]?.name ?? code}</b><div className="xs muted">{CHECKS[code]?.question}</div></td>
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
          <h2 className="section-title" style={{ fontSize: 17 }}>What went wrong, and what we changed</h2>
          <ul>
            <li><b>Missing lines.</b> On some invoices, long item names ran into the next column and a line was silently skipped. Now the system checks the lines add up to the subtotal, and stops any invoice where they don&rsquo;t.</li>
            <li><b>Two companies, one name.</b> Two different suppliers had almost identical names. Now it also checks the tax ID printed on the invoice.</li>
            <li><b>Too many false alarms on prices.</b> Small, harmless price changes were being flagged. Now a price must be both unusual and at least 10% higher. False alarms dropped from {before?.clean_invoices.with_a_failed_check ?? 58} to {now?.clean_invoices.with_a_failed_check ?? 0}.</li>
          </ul>
        </section>
        <section className="card card-pad prose">
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <AlertTriangle size={20} color="var(--warn)" aria-hidden />
            <h2 className="section-title" style={{ fontSize: 17 }}>The one it missed</h2>
          </div>
          <p style={{ marginTop: 8 }}>
            A supplier sent the same bill twice under a new number. The original arrived as a scanned photo that
            couldn&rsquo;t be read, so there was nothing to compare the copy against. It reached &ldquo;Ready to pay&rdquo;, but
            it still needed a person&rsquo;s approval, so it wasn&rsquo;t paid. The fix planned next: whenever a scanned invoice
            is typed in by hand, recheck everything already marked ready to pay.
          </p>
        </section>
      </div>

      <section className="section">
        <div className="callout callout-info">
          <ShieldCheck size={20} color="var(--primary)" aria-hidden />
          <div>
            <h4>Honest about the limits</h4>
            <p>
              The demo invoices are made up, so these numbers are a best case, not a promise for real invoices. The full
              method, raw results and design decisions are in the <a href={`${REPO}/blob/main/eval/report.md`}>evaluation
              report</a> and the <a href={REPO}>source code</a>. Developers can also use the <a href="/api/docs">API</a>.{" "}
              <Link href="/lab/">Try it yourself</Link> to see it catch mistakes live.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
