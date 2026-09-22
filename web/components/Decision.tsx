"use client";

import { useEffect, useState } from "react";
import { api, type DecisionEvent, readReviewer, saveReviewer } from "./api";
import { date } from "./format";
import { ACTIONS, DECISION_LABEL } from "./labels";

type Choice = "approved" | "held" | "escalated";

const CHOICES: { kind: Choice; title: string; help: string }[] = [
  { kind: "approved", title: "Approve", help: "Countersign for payment" },
  { kind: "held", title: "Hold", help: "Wait on the vendor" },
  { kind: "escalated", title: "Escalate", help: "Send to the controller" },
];

function disagrees(action: string, choice: Choice): boolean {
  if (action === "CLEAR_FOR_PAYMENT") return choice !== "approved";
  if (action === "ESCALATE_TO_CONTROLLER") return choice !== "escalated";
  if (action.startsWith("HOLD_")) return choice !== "held";
  return false;
}

function time(iso: string): string {
  return `${date(iso.slice(0, 10))}, ${iso.slice(11, 16)} UTC`;
}

/**
 * Records a decision through the API. The server applies the state machine and the
 * rules again; this form only explains them in advance, so a refusal is rare and,
 * when it happens, the server's reason is shown as it was given.
 */
export default function Decision({
  ws,
  invoiceId,
  action,
  events,
  onRecorded,
  preset,
}: {
  ws: string;
  invoiceId: string;
  action: string;
  events: DecisionEvent[];
  onRecorded: () => void;
  preset?: Choice | null;
}) {
  const [choice, setChoice] = useState<Choice | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState(false);

  useEffect(() => setReviewer(readReviewer()), []);
  useEffect(() => {
    setChoice(null);
    setNote("");
    setError(null);
    setWithdrawing(false);
  }, [invoiceId]);
  useEffect(() => {
    if (preset) setChoice(preset);
  }, [preset]);

  const current = events.length ? events[events.length - 1] : null;
  const decided = current && current.decision !== "withdrawn" ? current : null;
  const needsNote = withdrawing || (choice ? disagrees(action, choice) : false);

  async function submit(decision: Choice | "withdrawn") {
    setBusy(true);
    setError(null);
    try {
      saveReviewer(reviewer.trim());
      await api(`/api/workspaces/${ws}/decisions`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ invoiceId, decision, reviewer, note }),
      });
      setChoice(null);
      setNote("");
      setWithdrawing(false);
      onRecorded();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const history = events.length > 0 && (
    <div className="events" aria-label="Decision history">
      {events.map((e) => (
        <span key={e.seq}>
          {time(e.at)} · {e.decision === "withdrawn" ? "Withdrawn" : DECISION_LABEL[e.decision]?.phrase} by {e.reviewer}
          {e.overrules_recommendation && " · overruled the recommendation"}
          {e.note && ` · “${e.note}”`}
        </span>
      ))}
    </div>
  );

  if (decided && !withdrawing) {
    const label = DECISION_LABEL[decided.decision];
    return (
      <div>
        <div className="signature" data-kind={decided.decision}>
          <span className="stamp">{label.stamp}</span>
          <span className="who">{decided.reviewer}</span>
          <span className="when">
            {label.phrase} · {time(decided.at)}
          </span>
          {decided.note && <span className="why">{decided.note}</span>}
        </div>
        {history}
        <p style={{ marginTop: 12 }}>
          <button className="link-button" onClick={() => setWithdrawing(true)}>
            Withdraw this decision
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="decide">
      {withdrawing ? (
        <p>Withdrawing returns the invoice to where the system left it. The withdrawal is kept in the history.</p>
      ) : (
        <div className="choices" role="group" aria-label="Decision">
          {CHOICES.map((c) => (
            <button
              key={c.kind}
              className="choice"
              data-kind={c.kind}
              aria-pressed={choice === c.kind}
              onClick={() => setChoice(c.kind)}
            >
              <b>{c.title}</b>
              <span>{c.help}</span>
            </button>
          ))}
        </div>
      )}

      {(choice || withdrawing) && (
        <>
          <div className="decide-row">
            <div className="field">
              <label className="label" htmlFor="reviewer">Signed by</label>
              <input id="reviewer" className="input" value={reviewer} autoComplete="name"
                onChange={(e) => setReviewer(e.target.value)} placeholder="Your name" />
            </div>
            <div className="field">
              <label className="label" htmlFor="note">
                {needsNote ? "Reason (required)" : "Note (optional)"}
              </label>
              <textarea id="note" className="textarea" value={note} onChange={(e) => setNote(e.target.value)}
                aria-describedby="note-help" />
              <span id="note-help" className="help">
                {withdrawing
                  ? "Say why it is being withdrawn. At least 10 characters."
                  : needsNote
                    ? `This overrules “${ACTIONS[action]?.verdict ?? action}”. At least 10 characters.`
                    : "Kept with the decision in the audit trail."}
              </span>
            </div>
          </div>
          {error && <p className="flash" role="alert">{error}</p>}
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-ink" disabled={busy || reviewer.trim().length < 2}
              onClick={() => submit(withdrawing ? "withdrawn" : choice!)}>
              {busy ? "Recording…" : withdrawing ? "Withdraw decision" : "Sign and record"}
            </button>
            <button className="btn" onClick={() => (setChoice(null), setWithdrawing(false))}>Cancel</button>
          </div>
        </>
      )}
      <p className="notice">
        Recorded on the server, checked by the same state machine as the pipeline, and kept in this
        workspace&rsquo;s audit trail. Nothing is paid: this system has no code path that pays.
      </p>
      {history}
    </div>
  );
}
