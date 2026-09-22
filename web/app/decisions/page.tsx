"use client";

import { AlertOctagon, CheckCircle2, Download, History, PauseCircle, Undo2 } from "lucide-react";
import Link from "next/link";
import { useDecisions, useWorkspace } from "@/components/api";
import { NEXT_STEP } from "@/components/explain";
import { date } from "@/components/format";
import { Empty, Pill } from "@/components/ui";

const LABEL = {
  approved: { word: "Approved", tone: "ok" as const },
  held: { word: "On hold", tone: "warn" as const },
  escalated: { word: "Escalated", tone: "bad" as const },
};

export default function Decisions() {
  const ws = useWorkspace();
  const { data, error } = useDecisions(ws);
  const log = [...(data?.log ?? [])].reverse();
  const current = Object.values(data?.current ?? {});
  const count = (d: string) => current.filter((e) => e.decision === d).length;
  const overruled = current.filter((e) => e.overrules_recommendation).length;

  const stats = [
    { icon: CheckCircle2, tone: "tone-ok", label: "Approved", value: count("approved"), meaning: "Checked and cleared for payment." },
    { icon: PauseCircle, tone: "tone-warn", label: "On hold", value: count("held"), meaning: "Waiting for the supplier to fix something." },
    { icon: AlertOctagon, tone: "tone-bad", label: "Escalated", value: count("escalated"), meaning: "Sent to the finance controller." },
    { icon: Undo2, tone: "tone-muted", label: "Went against the suggestion", value: overruled, meaning: "Each one has a written reason." },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Decision history</h1>
          <p>
            Every decision made in your workspace, newest first. Entries are never edited or deleted; undoing a
            decision adds a new entry. This is the record an auditor would ask for.
          </p>
        </div>
        {ws && log.length > 0 && (
          <div className="end">
            <a className="btn" href={`/api/workspaces/${ws}/decisions.csv`}><Download size={16} aria-hidden /> Download as CSV</a>
          </div>
        )}
      </div>

      <div className="grid-4">
        {stats.map(({ icon: Icon, tone, label, value, meaning }) => (
          <div className="card stat" key={label}>
            <div className="stat-top"><span className={`stat-icon ${tone}`}><Icon size={18} aria-hidden /></span>{label}</div>
            <div className="stat-value">{data ? value : "…"}</div>
            <div className="stat-meaning">{meaning}</div>
          </div>
        ))}
      </div>

      <section className="card section">
        <div className="card-head"><History size={18} className="muted" aria-hidden /><h2>All decisions</h2></div>
        {error && <p className="error-box" style={{ margin: 16 }}>{error}</p>}
        {data && log.length === 0 && (
          <Empty icon={History} title="No decisions yet">
            <p className="small">Open an invoice, then choose Approve, Put on hold or Escalate at the bottom.</p>
            <Link className="btn btn-primary btn-sm" href="/review/">Go to review</Link>
          </Empty>
        )}
        {log.length > 0 && (
          <div className="table-wrap">
            <table className="t">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Invoice</th>
                  <th>Decision</th>
                  <th>By</th>
                  <th>System suggested</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {log.map((e) => {
                  const l = LABEL[e.decision as keyof typeof LABEL];
                  return (
                    <tr key={`${e.invoice_id}-${e.seq}`}>
                      <td className="num small">{date(e.at.slice(0, 10))}, {e.at.slice(11, 16)}</td>
                      <td><Link className="mono" href={`/review/?id=${e.invoice_id}`}>{e.invoice_id}</Link></td>
                      <td>{l ? <Pill tone={l.tone}>{l.word}</Pill> : <Pill tone="muted">Undone</Pill>}</td>
                      <td>{e.reviewer}</td>
                      <td className="small">
                        {NEXT_STEP[e.recommended_action]?.what ?? e.recommended_action}
                        {e.overrules_recommendation && <div className="xs" style={{ color: "var(--warn)", fontWeight: 600 }}>Went against this</div>}
                      </td>
                      <td className="small soft">{e.note || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
