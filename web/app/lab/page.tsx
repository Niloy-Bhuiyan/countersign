"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, useWorkspace } from "@/components/api";
import type { CaseDetail } from "@/components/CaseView";
import { money } from "@/components/format";
import { ACTIONS, CHECKS, Glyph, REASONS, ruleLabel } from "@/components/labels";

type Options = {
  vendors: { id: string; name: string; category: string; items: string[]; historyReady: boolean }[];
  tampers: { id: string; label: string; effect: string; expect: string }[];
};

type Outcome = CaseDetail & { scenario?: { tamper: string; label: string; expect: string } };

function Result({ c, ws }: { c: Outcome; ws: string }) {
  const failed = c.results.filter((r) => r.outcome === "failed");
  const abstained = c.results.filter((r) => r.outcome === "abstained");
  const cleared = c.state === "cleared";
  return (
    <div className="outcome" aria-live="polite">
      <p className={`verdict ${cleared ? "green" : "red"}`}>
        {cleared ? "Cleared every check." : c.reason && c.reason !== "check_findings"
          ? `Sent to review: ${(REASONS[c.reason] ?? c.reason).toLowerCase()}.`
          : `Sent to review with ${failed.length} failed check${failed.length === 1 ? "" : "s"}.`}
      </p>
      <dl className="outcome-grid">
        {c.scenario && (
          <>
            <dt>Asked for</dt>
            <dd>{c.scenario.label}</dd>
            <dt>Expected</dt>
            <dd>{c.scenario.expect}</dd>
          </>
        )}
        <dt>Read as</dt>
        <dd>
          <span className="id">{c.number ?? "unread"}</span> from {c.vendor ?? "an unidentified vendor"},{" "}
          <span className="fig">{c.total ? money(c.total, c.currency) : "no total"}</span>
        </dd>
        <dt>Found</dt>
        <dd style={{ display: "grid", gap: 4 }}>
          {failed.length === 0 && abstained.length === 0 && <span className="green">Nothing. All four checks passed.</span>}
          {failed.map((r, i) => (
            <span key={i} className="red" style={{ display: "flex", gap: 6, alignItems: "start" }}>
              <Glyph kind="failed" /> {CHECKS[r.check_code]}: {ruleLabel(`${r.check_code}/${r.rule}`)}
            </span>
          ))}
          {abstained.map((r, i) => (
            <span key={`a${i}`} className="muted" style={{ display: "flex", gap: 6 }}>
              <Glyph kind="abstained" /> {CHECKS[r.check_code]} could not judge: {ruleLabel(`${r.check_code}/${r.rule}`).toLowerCase()}
            </span>
          ))}
        </dd>
        <dt>Recommends</dt>
        <dd>{ACTIONS[c.action]?.verdict ?? c.action}</dd>
      </dl>
      <p style={{ display: "flex", gap: 16 }}>
        <Link href={`/?id=${c.id}`}>Open in review</Link>
        <a href={`/api/workspaces/${ws}/files/${c.file}`}>Download the {c.format.toUpperCase()}</a>
      </p>
    </div>
  );
}

export default function Lab() {
  const ws = useWorkspace();
  const [options, setOptions] = useState<Options | null>(null);
  const [vendor, setVendor] = useState("");
  const [tamper, setTamper] = useState("clean");
  const [busy, setBusy] = useState<"lab" | "upload" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [over, setOver] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api<Options>("/api/lab/options")
      .then((o) => {
        setOptions(o);
        setVendor(o.vendors[0]?.id ?? "");
      })
      .catch((e: Error) => setError(`The lab service is unavailable: ${e.message}`));
  }, []);

  const chosen = useMemo(() => options?.vendors.find((v) => v.id === vendor), [options, vendor]);

  async function issue() {
    if (!ws) return;
    setBusy("lab");
    setError(null);
    setOutcome(null);
    try {
      setOutcome(
        await api<Outcome>(`/api/workspaces/${ws}/lab`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ vendorId: vendor, tamper }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function upload(f: File | undefined) {
    if (!ws || !f) return;
    setBusy("upload");
    setError(null);
    setOutcome(null);
    const form = new FormData();
    form.append("file", f);
    try {
      setOutcome(await api<Outcome>(`/api/workspaces/${ws}/documents`, { method: "POST", body: form }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
      if (file.current) file.current.value = "";
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">Invoice lab</h1>
      <p className="lede">
        Raise an order with a real vendor, receive the goods, and have the supplier bill for them, with one
        thing wrong or nothing at all. The server writes the supplier&rsquo;s invoice as a PDF, then reads
        that PDF back through the same pipeline the evaluation measured. Nothing is passed along that a real
        supplier would not send.
      </p>

      <div className="lab">
        <section>
          <div className="section-head"><h2>Issue an invoice</h2></div>
          <div className="field" style={{ marginBottom: 18 }}>
            <label className="label" htmlFor="vendor">Vendor</label>
            <select id="vendor" className="select" value={vendor} onChange={(e) => setVendor(e.target.value)} disabled={!options}>
              {options?.vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name} — {v.category}{v.historyReady ? "" : " (short price history)"}</option>
              ))}
            </select>
            {chosen && (
              <span className="help">
                Supplies {chosen.items.join(", ").toLowerCase()}.
                {!chosen.historyReady && " Too few earlier prices for the variance check to judge: an inflated order will be held as “could not judge”, not failed."}
              </span>
            )}
          </div>

          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend className="label" style={{ marginBottom: 8 }}>What the supplier gets wrong</legend>
            <div className="scenarios">
              {options?.tampers.map((t) => (
                <label key={t.id} className="scenario">
                  <input type="radio" name="tamper" value={t.id} checked={tamper === t.id} onChange={() => setTamper(t.id)} />
                  <span>
                    <b>{t.label}</b>
                    <p>{t.effect}</p>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div style={{ marginTop: 18, display: "flex", gap: 12, alignItems: "center" }}>
            <button className="btn btn-ink" onClick={issue} disabled={!options || !ws || busy !== null}>
              {busy === "lab" ? "Issuing and reading…" : "Issue and process"}
            </button>
            <span className="help">Takes a few seconds: render, read, check, recommend.</span>
          </div>

          <div className="section-head" style={{ marginTop: 40 }}><h2>Or upload your own</h2></div>
          <label
            className="dropzone"
            data-over={over}
            onDragOver={(e) => (e.preventDefault(), setOver(true))}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setOver(false);
              upload(e.dataTransfer.files[0]);
            }}
          >
            <input ref={file} type="file" accept=".pdf,.xlsx,.csv" hidden onChange={(e) => upload(e.target.files?.[0])} />
            {busy === "upload" ? "Reading and checking…" : "Drop a PDF, XLSX or CSV invoice, or choose a file"}
          </label>
          <p className="help" style={{ marginTop: 8 }}>
            Any file is read and checked against this buyer&rsquo;s orders. Try downloading an invoice from the
            review screen and uploading it again: it is caught as a duplicate.
          </p>
        </section>

        <section>
          <div className="section-head"><h2>What happened</h2></div>
          {error && <p className="flash" role="alert">{error}</p>}
          {outcome && ws ? (
            <>
              <Result c={outcome} ws={ws} />
              {outcome.format === "pdf" && (
                <iframe className="doc-frame" style={{ marginTop: 18, height: 560 }}
                  src={`/api/workspaces/${ws}/files/${outcome.file}`} title="The invoice as issued" />
              )}
            </>
          ) : (
            !error && (
              <p className="muted">
                Issue an invoice to see what the checks find. Each one joins your review ledger under
                &ldquo;Mine&rdquo;, where you can decide it.
              </p>
            )
          )}
        </section>
      </div>
    </div>
  );
}
