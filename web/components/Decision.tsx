"use client";

import { AlertOctagon, CheckCircle2, PauseCircle, PenLine, Undo2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type DecisionEvent, readReviewer, saveReviewer } from "./api";
import { NEXT_STEP } from "./explain";
import { date } from "./format";

type Choice = "approved" | "held" | "escalated";

const CHOICES: { kind: Choice; title: string; help: string; icon: React.ElementType }[] = [
  { kind: "approved", title: "Approve payment", help: "The invoice is correct. Pay it.", icon: CheckCircle2 },
  { kind: "held", title: "Put on hold", help: "Wait for the supplier to fix or explain something.", icon: PauseCircle },
  { kind: "escalated", title: "Escalate", help: "Send to the finance controller to decide.", icon: AlertOctagon },
];

const DONE: Record<Choice, { word: string; tone: string; icon: React.ElementType }> = {
  approved: { word: "Approved for payment", tone: "ok", icon: CheckCircle2 },
  held: { word: "Put on hold", tone: "warn", icon: PauseCircle },
  escalated: { word: "Escalated to the controller", tone: "bad", icon: AlertOctagon },
};

function suggested(action: string): Choice | null {
  if (action === "CLEAR_FOR_PAYMENT") return "approved";
  if (action === "ESCALATE_TO_CONTROLLER") return "escalated";
  if (action.startsWith("HOLD_")) return "held";
  return null;
}

function when(iso: string): string {
  return `${date(iso.slice(0, 10))} at ${iso.slice(11, 16)} UTC`;
}

/**
 * Records a decision on the server. The server checks the same rules again (a name, a
 * reason when you disagree with the suggestion, no deciding twice), so this form only
 * explains them up front and shows the server's reason if it refuses.
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
  const [undoing, setUndoing] = useState(false);

  useEffect(() => setReviewer(readReviewer()), []);
  useEffect(() => {
    setChoice(null);
    setNote("");
    setError(null);
    setUndoing(false);
  }, [invoiceId]);
  useEffect(() => {
    if (preset) setChoice(preset);
  }, [preset]);

  const hint = suggested(action);
  const latest = events.length ? events[events.length - 1] : null;
  const decided = latest && latest.decision !== "withdrawn" ? latest : null;
  const needsReason = undoing || (choice !== null && hint !== null && choice !== hint);

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
      setUndoing(false);
      onRecorded();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const history = events.length > 0 && (
    <details className="tech">
      <summary>History of this invoice ({events.length})</summary>
      <div className="body history">
        {events.map((e) => (
          <div key={e.seq}>
            <span>
              {when(e.at)}: <b>{e.decision === "withdrawn" ? "Decision undone" : DONE[e.decision as Choice]?.word}</b> by{" "}
              {e.reviewer}
              {e.overrules_recommendation && " (different from the suggestion)"}
              {e.note && `. “${e.note}”`}
            </span>
          </div>
        ))}
      </div>
    </details>
  );

  if (decided && !undoing) {
    const d = DONE[decided.decision as Choice];
    const Icon = d.icon;
    return (
      <div className="stack">
        <div className={`callout callout-${d.tone}`}>
          <Icon size={22} color={`var(--${d.tone})`} aria-hidden />
          <div>
            <h4>{d.word}</h4>
            <p>
              Signed by <b>{decided.reviewer}</b> on {when(decided.at)}.
              {decided.note && <> Reason: &ldquo;{decided.note}&rdquo;</>}
            </p>
          </div>
          <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={() => setUndoing(true)}>
            <Undo2 size={15} aria-hidden /> Undo
          </button>
        </div>
        {history}
      </div>
    );
  }

  return (
    <div className="stack">
      {undoing ? (
        <div className="callout callout-info">
          <Undo2 size={20} color="var(--primary)" aria-hidden />
          <div>
            <h4>Undo this decision?</h4>
            <p>The invoice goes back to where it was. The undo is kept in the history, so nothing disappears.</p>
          </div>
        </div>
      ) : (
        <div className="decide-grid" role="group" aria-label="Your decision">
          {CHOICES.map(({ kind, title, help, icon: Icon }) => (
            <button key={kind} className="choice" data-kind={kind} aria-pressed={choice === kind} onClick={() => setChoice(kind)}>
              <span className="t">
                <Icon size={18} aria-hidden /> {title}
              </span>
              <span className="d">{help}</span>
              {hint === kind && <span className="pill pill-info" style={{ width: "fit-content" }}>Suggested</span>}
            </button>
          ))}
        </div>
      )}

      {(choice || undoing) && (
        <>
          <div className="decide-fields">
            <div className="field">
              <label htmlFor="reviewer">Your name</label>
              <input id="reviewer" className="input" value={reviewer} autoComplete="name" placeholder="e.g. Nusrat Rahman"
                onChange={(e) => setReviewer(e.target.value)} />
              <span className="hint">Every decision is signed.</span>
            </div>
            <div className="field">
              <label htmlFor="note">{needsReason ? "Reason (required)" : "Note (optional)"}</label>
              <textarea id="note" className="textarea" value={note} onChange={(e) => setNote(e.target.value)}
                placeholder={needsReason ? "Why are you choosing differently from the suggestion?" : "Anything worth remembering"} />
              <span className="hint">
                {undoing
                  ? "Say why you're undoing it (at least 10 characters)."
                  : needsReason
                    ? `The suggestion was “${NEXT_STEP[action]?.what}”. Choosing differently needs a reason of at least 10 characters.`
                    : "Saved with your decision."}
              </span>
            </div>
          </div>
          {error && <p className="error-box" role="alert">Not saved: {error}</p>}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="btn btn-primary" disabled={busy || reviewer.trim().length < 2}
              onClick={() => submit(undoing ? "withdrawn" : choice!)}>
              {busy ? <span className="spinner" aria-hidden /> : <PenLine size={16} aria-hidden />}
              {busy ? "Saving…" : undoing ? "Undo decision" : "Sign and save"}
            </button>
            <button className="btn btn-ghost" onClick={() => (setChoice(null), setUndoing(false))}>Cancel</button>
          </div>
        </>
      )}
      <p className="hint">
        Saved on the server in your workspace&rsquo;s decision history. This demo never pays anything.
      </p>
      {history}
    </div>
  );
}
