"use client";

import { ArrowRight, ArrowUpRight, Check, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, useJson } from "@/components/api";
import type { CaseDetail } from "@/components/CaseView";
import { CHECK_ORDER, CHECKS, findingSentence, MISTAKES, NEXT_STEP, REASONS, shortIssue, statusOf } from "@/components/explain";
import { compact, money } from "@/components/format";
import { CountUp, PenStroke, useSeen } from "@/components/motion";

type Summary = {
  documents: number;
  cleared: number;
  needsReview: number;
  atRiskBDT: string;
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

function initials(name: string | null): string {
  return (name ?? "?").split(/\s+/).filter((w) => /^[A-Za-z]/.test(w)).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

/** A live window onto the review screen, built from the same data as the real page. */
function Preview({ rows }: { rows: Row[] }) {
  const [id, setId] = useState(rows[0].id);
  const [c, setC] = useState<CaseDetail | null>(null);

  useEffect(() => {
    let live = true;
    api<CaseDetail>(`/data/case/${id}.json`).then((d) => live && setC(d)).catch(() => live && setC(null));
    return () => {
      live = false;
    };
  }, [id]);

  const row = rows.find((r) => r.id === id)!;
  const findings = c ? c.results.filter((r) => r.outcome !== "passed") : [];
  const next = c ? NEXT_STEP[c.action] : null;

  return (
    <div className="window" aria-label="Preview of the review screen">
      <div className="window-bar"><i /><i /><i /><span>Countersign · Review</span></div>
      <div className="window-body">
        <div className="window-side">
          <div className="fake-search"><Search size={14} aria-hidden /> Search</div>
          {rows.map((r) => {
            const s = statusOf(r);
            return (
              <button key={r.id} className="w-item" aria-current={r.id === id} onClick={() => setId(r.id)}>
                <span className={`av av-${s.tone}`} aria-hidden>{initials(r.vendor)}</span>
                <span className="who">{r.vendor ?? "Unreadable file"}</span>
                <span className="amt">{r.total ? compact(r.total) : ""}</span>
                <span className="what">{shortIssue(r.failed, r.abstained, r.reason)}</span>
              </button>
            );
          })}
        </div>
        <div className="window-main">
          <div className="top">
            <span className={`dot dot-${statusOf(row).tone}`} aria-hidden />
            {row.vendor}
            <span className="end">{statusOf(row).label}</span>
          </div>
          <div className="thread" aria-live="polite" key={id}>
            <span className="time">Invoice {row.number ?? row.id}</span>
            <div className="bubble">
              <span className="l">Amount billed</span>
              {row.currency} {money(row.total)}
            </div>
            {c && row.reason && row.reason !== "check_findings" && (
              <div className="bubble"><span className="l">Couldn&rsquo;t check</span>{REASONS[row.reason]?.long}</div>
            )}
            {findings.slice(0, 2).map((r, i) => (
              <div className="bubble" key={i}>
                <span className="l">{CHECKS[r.check_code]?.name}</span>
                {findingSentence(r)}
              </div>
            ))}
            {c && !findings.length && !(row.reason && row.reason !== "check_findings") && (
              <div className="bubble"><span className="l">All four checks</span>Passed. Nothing wrong found.</div>
            )}
            {next && (
              <div className="bubble me">
                <span className="l">Suggested next step</span>
                {next.what}
              </div>
            )}
            <div className="act">
              <Link className="btn btn-sm" href={`/review/?id=${id}`}>Open this invoice <ArrowRight size={15} aria-hidden /></Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Overview() {
  const { data: s } = useJson<Summary>("/data/summary.json");
  const { data: rows } = useJson<Row[]>("/data/queue.json");
  const { data: e } = useJson<Evaluation>("/data/evaluation.json");
  const [mistake, setMistake] = useState(MISTAKES[0].id);

  const examples = useMemo(() => {
    if (!rows) return [];
    const picks: Row[] = [];
    const add = (f: (r: Row) => boolean) => {
      const r = rows.find((x) => f(x) && !picks.includes(x) && x.vendor);
      if (r) picks.push(r);
    };
    add((r) => r.failed.includes("THREE_WAY_MATCH/quantity_over_received"));
    add((r) => r.failed.includes("PRICE_VARIANCE/above_history"));
    add((r) => r.failed.includes("TAX_ARITHMETIC/tax_total"));
    add((r) => r.failed.some((k) => k.startsWith("DUPLICATE")));
    add((r) => r.state === "cleared");
    add((r) => !r.failed.length && r.abstained.length > 0);
    return picks;
  }, [rows]);

  const flagged = useMemo(() => {
    const out: Record<string, number> = {};
    s?.findingsByRule.forEach((f) => {
      const code = f.label.split("/")[0];
      out[code] = (out[code] ?? 0) + f.value;
    });
    return out;
  }, [s]);

  const now = e?.["checks-current"];
  const chosen = MISTAKES.find((m) => m.id === mistake)!;
  const orb = useSeen<HTMLDivElement>();

  return (
    <main className="page" style={{ paddingTop: 0 }}>
      <section className="hero">
        <Link className="kicker-link" href="/method/">
          <b>Live demo</b> · See how accurate it is <span className="arrow"><ArrowUpRight size={13} aria-hidden /></span>
        </Link>
        <h1>
          Check every invoice
          <br />
          before you <span className="mark" aria-hidden><Check size="0.5em" strokeWidth={3} /></span>{" "}
          <span className="signed">pay<PenStroke /></span>
        </h1>
        <p className="lead">
          Countersign compares each supplier bill with what you ordered and received, and tells you what&rsquo;s wrong.
        </p>
        <div className="ctas">
          <Link className="btn btn-primary btn-lg" href="/review/">Review invoices</Link>
          <Link className="btn btn-lg" href="/lab/">Try it yourself</Link>
        </div>
        {examples.length > 0 && <Preview rows={examples} />}
      </section>

      <section className="section-lg card feature">
        <div>
          <h2>Nothing is paid without a signature</h2>
          <p>Countersign only suggests. A person approves, holds or escalates, and every decision is signed and kept.</p>
        </div>
        <div ref={orb.ref} className={`orb${orb.seen ? " seen" : ""}`} aria-hidden><Check size={96} strokeWidth={2.5} /></div>
      </section>

      <section className="section-lg">
        <h2 className="section-title center">Four checks on every invoice</h2>
        <div className="tiles">
          {CHECK_ORDER.map((code) => (
            <div className="tile" key={code}>
              <h3>{CHECKS[code].name}</h3>
              <p>{CHECKS[code].question}</p>
              <div className="figure"><b>{flagged[code] ?? "…"}</b> invoices flagged</div>
            </div>
          ))}
        </div>
      </section>

      <section className="section-lg">
        <h2 className="section-title">Plant a mistake. Watch it get caught.</h2>
        <div className="chips" role="group" aria-label="Mistakes">
          {MISTAKES.map((m) => (
            <button key={m.id} className="chip" aria-pressed={m.id === mistake} onClick={() => setMistake(m.id)}>
              {m.label}
            </button>
          ))}
        </div>
        <p className="chip-body"><b>{chosen.label}.</b> {chosen.effect}</p>
        <Link className="btn" style={{ marginTop: 24 }} href={`/lab/?t=${chosen.id}`}>Try this one</Link>
      </section>

      <section className="section-lg numbers">
        <div className="n"><b>{s ? <CountUp text={String(s.documents)} /> : "…"}</b><span>invoices checked</span></div>
        <div className="n">
          <b>{now ? <CountUp text={`${now.defects.planted - now.defects.reached_cleared}/${now.defects.planted}`} /> : "…"}</b>
          <span>planted mistakes caught</span>
        </div>
        <div className="n"><b>{now?.clean_invoices.with_a_failed_check ?? "…"}</b><span>false alarms</span></div>
        <div className="n"><b>{s ? <CountUp text={`BDT ${compact(s.atRiskBDT)}`} /> : "…"}</b><span>waiting for a decision</span></div>
      </section>
    </main>
  );
}
