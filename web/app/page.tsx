"use client";

import {
  ArrowRight,
  BadgeCheck,
  Banknote,
  Calculator,
  CheckCircle2,
  Copy,
  FileSearch,
  FileText,
  FlaskConical,
  PackageCheck,
  PenLine,
  ScanText,
  ShieldCheck,
  TrendingUp,
  Upload,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { useJson } from "@/components/api";
import { CHECK_ORDER, CHECKS, shortIssue, statusOf } from "@/components/explain";
import { compact, money } from "@/components/format";
import { StatusPill, Tip } from "@/components/ui";

type Summary = {
  documents: number;
  cleared: number;
  needsReview: number;
  spendBDT: string;
  atRiskBDT: string;
  withFindings: number;
  findingsByRule: { label: string; value: number }[];
};

type Row = {
  id: string;
  number: string | null;
  vendor: string | null;
  total: string | null;
  currency: string | null;
  state: string;
  reason: string | null;
  failed: string[];
  abstained: string[];
};

type Evaluation = {
  "checks-current": {
    defects: { planted: number; reached_cleared: number };
    clean_invoices: { with_a_failed_check: number };
  };
};

const CHECK_ICONS: Record<string, React.ElementType> = {
  THREE_WAY_MATCH: PackageCheck,
  PRICE_VARIANCE: TrendingUp,
  DUPLICATE_INVOICE: Copy,
  TAX_ARITHMETIC: Calculator,
};

const STEPS = [
  { icon: Upload, title: "An invoice arrives", text: "A supplier sends a bill as a PDF, Excel sheet or CSV file." },
  { icon: ScanText, title: "It's read automatically", text: "Countersign pulls out the supplier, items, quantities, prices and totals, and checks the sums add up." },
  { icon: ShieldCheck, title: "Four checks run", text: "It compares the bill with what we ordered, what arrived, past prices and earlier invoices." },
  { icon: PenLine, title: "A person decides", text: "You see what's wrong in plain words and approve, hold or escalate. Nothing is paid automatically." },
];

export default function Overview() {
  const { data: s } = useJson<Summary>("/data/summary.json");
  const { data: rows } = useJson<Row[]>("/data/queue.json");
  const { data: e } = useJson<Evaluation>("/data/evaluation.json");

  const examples = useMemo(() => {
    if (!rows) return [];
    const pick = (f: (r: Row) => boolean) => rows.find(f);
    return [
      pick((r) => r.failed.some((k) => k.startsWith("PRICE_VARIANCE"))),
      pick((r) => r.failed.some((k) => k.startsWith("DUPLICATE"))),
      pick((r) => r.state === "cleared"),
    ].filter(Boolean) as Row[];
  }, [rows]);

  const caughtBy = useMemo(() => {
    const out: Record<string, number> = {};
    s?.findingsByRule.forEach((f) => {
      const code = f.label.split("/")[0];
      out[code] = (out[code] ?? 0) + f.value;
    });
    return out;
  }, [s]);

  const now = e?.["checks-current"];
  const caught = now ? now.defects.planted - now.defects.reached_cleared : null;

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="pill pill-info" style={{ marginBottom: 16 }}>Accounts payable · Live demo</span>
          <h1>
            Check every supplier invoice <span>before you pay it.</span>
          </h1>
          <p className="lead">
            Countersign reads the invoices your suppliers send, compares each one with what you actually ordered and
            received, and tells you in plain words if something is wrong: overcharging, billing for goods that never
            arrived, wrong VAT, or the same bill sent twice. A person always makes the final call.
          </p>
          <div className="ctas">
            <Link className="btn btn-primary btn-lg" href="/review/">
              Start reviewing invoices <ArrowRight size={18} aria-hidden />
            </Link>
            <Link className="btn btn-accent btn-lg" href="/lab/">
              <FlaskConical size={18} aria-hidden /> Try it with a test invoice
            </Link>
          </div>
          <p className="small muted" style={{ marginTop: 14 }}>
            This demo uses 500 made-up invoices from 40 fictional suppliers. No real company is involved.
          </p>
        </div>

        <div className="card hero-card" aria-label="Examples from the review queue">
          <div className="small" style={{ fontWeight: 700 }}>What a reviewer sees</div>
          {examples.map((r) => (
            <Link key={r.id} href={`/review/?id=${r.id}`} className="mini-row" style={{ color: "inherit", textDecoration: "none" }}>
              <FileText size={20} className="muted" aria-hidden />
              <span style={{ minWidth: 0 }}>
                <span className="who" style={{ display: "block" }}>{r.vendor}</span>
                <span className="what">
                  {r.total ? `${r.currency} ${money(r.total)}` : ""} · {shortIssue(r.failed, r.abstained, r.reason)}
                </span>
              </span>
              <StatusPill status={statusOf(r)} />
            </Link>
          ))}
          {!rows && <p className="small muted">Loading examples…</p>}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Right now in this demo</h2>
        <p className="section-sub">What the numbers mean, in one line each. Tap the <b>i</b> for more.</p>
        <div className="grid-4">
          <div className="card stat">
            <div className="stat-top">
              <span className="stat-icon tone-primary"><FileSearch size={18} aria-hidden /></span>
              Invoices received
              <Tip>Every supplier bill in this demo, whether it was a PDF, a spreadsheet or a file that couldn't be opened.</Tip>
            </div>
            <div className="stat-value">{s?.documents ?? "…"}</div>
            <div className="stat-meaning">Bills from suppliers waiting to be checked and paid.</div>
          </div>
          <div className="card stat">
            <div className="stat-top">
              <span className="stat-icon tone-ok"><BadgeCheck size={18} aria-hidden /></span>
              Ready to pay
              <Tip>These passed all four checks. They still wait for a person to approve them: <b>nothing is paid automatically</b>.</Tip>
            </div>
            <div className="stat-value">
              {s?.cleared ?? "…"}
              {s && <small>{((s.cleared / s.documents) * 100).toFixed(0)}%</small>}
            </div>
            <div className="stat-meaning">Passed every check. Just need a person to approve.</div>
          </div>
          <div className="card stat">
            <div className="stat-top">
              <span className="stat-icon tone-bad"><XCircle size={18} aria-hidden /></span>
              Need a closer look
              <Tip>At least one check found a problem ({s?.withFindings ?? "…"} invoices), or couldn't decide, or the document couldn't be read.</Tip>
            </div>
            <div className="stat-value">{s?.needsReview ?? "…"}</div>
            <div className="stat-meaning">Something's wrong or unclear. A person should check.</div>
          </div>
          <div className="card stat">
            <div className="stat-top">
              <span className="stat-icon tone-warn"><Banknote size={18} aria-hidden /></span>
              Money on hold
              <Tip>The total of the invoices that need a closer look, in Bangladeshi taka. This money isn't paid until someone decides.</Tip>
            </div>
            <div className="stat-value">{s ? <>BDT {compact(s.atRiskBDT)}</> : "…"}</div>
            <div className="stat-meaning">Value of the invoices waiting for a decision.</div>
          </div>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">How it works</h2>
        <p className="section-sub">Four steps from a supplier&rsquo;s email to a decision.</p>
        <div className="steps">
          {STEPS.map(({ icon: Icon, title, text }, i) => (
            <div className="card step" key={title}>
              <span className="n">{String(i + 1).padStart(2, "0")}</span>
              <span className="stat-icon tone-primary"><Icon size={18} aria-hidden /></span>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">The four checks</h2>
        <p className="section-sub">Every invoice gets all four. Each one answers a simple question.</p>
        <div className="grid-2">
          {CHECK_ORDER.map((code) => {
            const Icon = CHECK_ICONS[code];
            return (
              <div className="card check-card" key={code}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="stat-icon tone-primary"><Icon size={18} aria-hidden /></span>
                  <h3>{CHECKS[code].name}</h3>
                  {caughtBy[code] !== undefined && (
                    <span className="pill pill-muted" style={{ marginLeft: "auto" }}>
                      Flagged {caughtBy[code]} invoices
                    </span>
                  )}
                </div>
                <p className="q">&ldquo;{CHECKS[code].question}&rdquo;</p>
                <p>{CHECKS[code].plain}</p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="section">
        <div className="callout callout-ok">
          <CheckCircle2 size={22} color="var(--ok)" aria-hidden />
          <div>
            <h4>How well does it work?</h4>
            <p>
              We planted {now?.defects.planted ?? 90} deliberate mistakes in the demo invoices. It stopped{" "}
              <b>{caught ?? 89}</b> of them before payment and raised{" "}
              <b>{now?.clean_invoices.with_a_failed_check ?? 0} false alarms</b> on correct invoices. The one it missed, and
              why, is explained on the <Link href="/method/">accuracy page</Link>.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
