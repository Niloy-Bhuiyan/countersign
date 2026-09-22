"use client";

import Link from "next/link";
import { useDecisions, useWorkspace } from "@/components/api";
import { date } from "@/components/format";
import { ACTIONS, DECISION_LABEL, Mark } from "@/components/labels";

export default function Decisions() {
  const ws = useWorkspace();
  const { data, error } = useDecisions(ws);
  const log = [...(data?.log ?? [])].reverse();
  const current = Object.values(data?.current ?? {});
  const count = (d: string) => current.filter((e) => e.decision === d).length;
  const overruled = current.filter((e) => e.overrules_recommendation).length;

  return (
    <div className="page">
      <h1 className="page-title">Decisions</h1>
      <p className="lede">
        Every decision recorded in this workspace, oldest last, including withdrawals. Entries are appended
        and never edited: this is the record an auditor would ask for.
      </p>

      {data && (
        <p className="statement" style={{ marginTop: 28 }}>
          <b>{count("approved")}</b> countersigned, <b>{count("held")}</b> held,{" "}
          <b>{count("escalated")}</b> escalated.{" "}
          {overruled > 0 ? (
            <span className="red">{overruled} overruled the system&rsquo;s recommendation, each with a reason.</span>
          ) : (
            "None overruled the system."
          )}
        </p>
      )}

      <section className="section">
        <div className="section-head">
          <h2>Audit trail</h2>
          {ws && <span className="aside"><a href={`/api/workspaces/${ws}/decisions.csv`}>Download CSV</a></span>}
        </div>
        {error && <p className="flash">{error}</p>}
        {data && log.length === 0 && (
          <p className="muted">
            No decisions yet. Open an invoice in <Link href="/">review</Link> and sign one.
          </p>
        )}
        {log.length > 0 && (
          <div className="sheet-wrap">
            <table className="sheet">
              <thead>
                <tr>
                  <th>When (UTC)</th>
                  <th>Invoice</th>
                  <th>Decision</th>
                  <th>Signed by</th>
                  <th>System recommended</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {log.map((e) => {
                  const d = DECISION_LABEL[e.decision];
                  return (
                    <tr key={`${e.invoice_id}-${e.seq}`}>
                      <td className="fig small">{date(e.at.slice(0, 10))} {e.at.slice(11, 16)}</td>
                      <td><Link className="id" href={`/?id=${e.invoice_id}`}>{e.invoice_id}</Link></td>
                      <td>{d ? <Mark kind={d.kind}>{d.stamp}</Mark> : <span className="muted">Withdrawn</span>}</td>
                      <td>{e.reviewer}</td>
                      <td className="small">
                        {ACTIONS[e.recommended_action]?.verdict ?? e.recommended_action}
                        {e.overrules_recommendation && <span className="red"> · overruled</span>}
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
