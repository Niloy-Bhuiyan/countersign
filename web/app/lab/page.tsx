"use client";

import { ArrowRight, CheckCircle2, CircleHelp, Download, FileUp, FlaskConical, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { api, useWorkspace } from "@/components/api";
import type { CaseDetail } from "@/components/CaseView";
import { findingSentence, NEXT_STEP, REASONS, statusOf } from "@/components/explain";
import { money } from "@/components/format";
import { Empty, StatusPill } from "@/components/ui";

type Options = {
  vendors: { id: string; name: string; category: string; items: string[]; historyReady: boolean }[];
  tampers: { id: string; label: string; effect: string; expect: string }[];
};

type Outcome = CaseDetail & { scenario?: { tamper: string; label: string; expect: string } };

/** The rule each planted mistake should trip; "cleared" means nothing should. */
const TARGET: Record<string, string> = {
  clean: "cleared",
  overbill: "THREE_WAY_MATCH/quantity_over_received",
  price_above_order: "THREE_WAY_MATCH/price_above_order",
  tax_error: "TAX_ARITHMETIC/tax_total",
  inflated_order: "PRICE_VARIANCE/above_history",
  currency: "THREE_WAY_MATCH/currency",
  resubmit: "DUPLICATE_INVOICE/same_number",
};

const FRIENDLY: Record<string, { label: string; effect: string; expect: string }> = {
  clean: { label: "Nothing wrong", effect: "A correct invoice. It should pass every check.", expect: "Expected: all four checks pass and it's marked ready to pay." },
  overbill: { label: "Bill for more than was delivered", effect: "One item is billed at 115% of what arrived.", expect: "Expected: the “Matches the order and delivery” check flags the extra quantity." },
  price_above_order: { label: "Charge more than agreed", effect: "One item costs 8% more than the purchase order says.", expect: "Expected: the “Matches the order and delivery” check flags the higher price." },
  tax_error: { label: "Get the VAT wrong", effect: "The VAT total is about a fifth too low; everything else adds up.", expect: "Expected: the “VAT adds up” check flags the wrong tax." },
  inflated_order: { label: "Inflate the order itself", effect: "The order and invoice agree, but the price is 60% above this supplier's normal price.", expect: "Expected: the paperwork agrees with itself, so only the “Price is normal” check can catch it." },
  currency: { label: "Use the wrong currency", effect: "Billed in US dollars against an order in taka.", expect: "Expected: the “Matches the order and delivery” check flags the currency." },
  resubmit: { label: "Send the last invoice again", effect: "The same file and invoice number, sent a second time.", expect: "Expected: the “Not a duplicate” check flags it as a copy." },
};

function Result({ c, ws }: { c: Outcome; ws: string }) {
  const tamper = c.scenario?.tamper ?? null;
  const target = tamper ? TARGET[tamper] : null;
  const found = c.results.filter((r) => r.outcome === "failed");
  const unsure = c.results.filter((r) => r.outcome === "abstained");
  const keys = found.map((r) => `${r.check_code}/${r.rule}`);
  const caught = target === "cleared" ? c.state === "cleared" : target ? keys.includes(target) : null;
  const unreadable = c.reason && c.reason !== "check_findings";

  return (
    <div className="stack">
      {caught !== null && (
        <div className={`callout ${caught ? "callout-ok" : "callout-warn"}`}>
          {caught ? <CheckCircle2 size={22} color="var(--ok)" aria-hidden /> : <CircleHelp size={22} color="var(--warn)" aria-hidden />}
          <div>
            <h4>
              {target === "cleared"
                ? caught ? "Correct: the invoice passed every check." : "The correct invoice was sent for review."
                : caught ? "Caught it. The planted mistake was found." : "Not caught by the expected check."}
            </h4>
            <p>{FRIENDLY[tamper ?? ""]?.expect ?? c.scenario?.expect}</p>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <div style={{ minWidth: 0 }}>
            <h3>{c.vendor ?? "Unknown supplier"}</h3>
            <p className="card-sub">
              Invoice <span className="mono">{c.number ?? "unreadable"}</span> · {c.total ? `${c.currency} ${money(c.total)}` : "no total"}
            </p>
          </div>
          <div className="end"><StatusPill status={statusOf(c)} /></div>
        </div>
        <div className="card-pad stack">
          <div>
            <p className="small" style={{ fontWeight: 700, marginBottom: 6 }}>What the checks found</p>
            <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", display: "grid", gap: 8 }}>
              {unreadable && <li className="small">{REASONS[c.reason!]?.long}</li>}
              {found.map((r, i) => (
                <li key={i} className="small" style={{ display: "flex", gap: 8 }}>
                  <XCircle size={16} color="var(--bad)" aria-hidden style={{ flex: "none", marginTop: 2 }} />{findingSentence(r)}
                </li>
              ))}
              {unsure.map((r, i) => (
                <li key={`u${i}`} className="small" style={{ display: "flex", gap: 8 }}>
                  <CircleHelp size={16} color="var(--warn)" aria-hidden style={{ flex: "none", marginTop: 2 }} />{findingSentence(r)}
                </li>
              ))}
              {!unreadable && !found.length && !unsure.length && (
                <li className="small" style={{ display: "flex", gap: 8 }}>
                  <CheckCircle2 size={16} color="var(--ok)" aria-hidden style={{ flex: "none", marginTop: 2 }} />Nothing wrong. All four checks passed.
                </li>
              )}
            </ul>
          </div>
          <div className="verdict-row">
            <div className="verdict-box">
              <div className="l">Suggested next step</div>
              <div className="v">{NEXT_STEP[c.action]?.what}</div>
            </div>
            <div className="verdict-box">
              <div className="l">Where it went</div>
              <div className="v">{c.state === "cleared" ? "Ready to pay" : "Needs a look"}, in your review list</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link className="btn btn-primary" href={`/review/?id=${c.id}`}>Open it in review <ArrowRight size={16} aria-hidden /></Link>
            <a className="btn" href={`/api/workspaces/${ws}/files/${c.file}`}><Download size={16} aria-hidden /> Download the {c.format.toUpperCase()}</a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Lab() {
  const ws = useWorkspace();
  const [options, setOptions] = useState<Options | null>(null);
  const [vendor, setVendor] = useState("");
  const [tamper, setTamper] = useState("overbill");
  const [busy, setBusy] = useState<"lab" | "upload" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [over, setOver] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if ((outcome || error) && window.innerWidth <= 1100) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [outcome, error]);

  useEffect(() => {
    api<Options>("/api/lab/options")
      .then((o) => {
        setOptions(o);
        setVendor(o.vendors[0]?.id ?? "");
      })
      .catch((e: Error) => setError(`The test service isn't responding: ${e.message}`));
  }, []);

  const chosen = useMemo(() => options?.vendors.find((v) => v.id === vendor), [options, vendor]);

  async function issue() {
    if (!ws) return;
    setBusy("lab");
    setError(null);
    setOutcome(null);
    try {
      setOutcome(await api<Outcome>(`/api/workspaces/${ws}/lab`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ vendorId: vendor, tamper }),
      }));
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
      <div className="page-head">
        <div>
          <h1>Try it yourself</h1>
          <p>
            Create a supplier invoice with a mistake of your choice, and watch whether Countersign catches it. It makes a
            real PDF, then reads it back exactly like an invoice from a supplier. Takes a few seconds.
          </p>
        </div>
      </div>

      <div className="lab">
        <div className="stack">
          <section className="card card-pad">
            <div className="step-label"><span className="n">1</span> Pick a supplier</div>
            <select className="select" style={{ width: "100%" }} value={vendor} onChange={(e) => setVendor(e.target.value)} disabled={!options} aria-label="Supplier">
              {options?.vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name} ({v.category}){v.historyReady ? "" : " — little price history"}</option>
              ))}
            </select>
            {chosen && (
              <p className="hint" style={{ marginTop: 8 }}>
                Sells {chosen.items.join(", ").toLowerCase()}.
                {!chosen.historyReady && " This supplier has few past prices, so the price check may say it can't decide."}
              </p>
            )}
          </section>

          <section className="card card-pad">
            <div className="step-label"><span className="n">2</span> Choose a mistake to plant</div>
            <div className="options" role="radiogroup" aria-label="Mistake">
              {options?.tampers.map((t) => (
                <label key={t.id} className="option">
                  <input type="radio" name="tamper" value={t.id} checked={tamper === t.id} onChange={() => setTamper(t.id)} />
                  <span>
                    <b>{FRIENDLY[t.id]?.label ?? t.label}</b>
                    <p>{FRIENDLY[t.id]?.effect ?? t.effect}</p>
                  </span>
                </label>
              ))}
            </div>
          </section>

          <section className="card card-pad">
            <div className="step-label"><span className="n">3</span> Create it and check it</div>
            <button className="btn btn-accent btn-lg" style={{ width: "100%" }} onClick={issue} disabled={!options || !ws || busy !== null}>
              {busy === "lab" ? <span className="spinner" aria-hidden /> : <FlaskConical size={18} aria-hidden />}
              {busy === "lab" ? "Creating and checking…" : "Create the invoice and check it"}
            </button>
          </section>

          <section className="card card-pad">
            <div className="step-label" style={{ marginBottom: 8 }}>Or check your own file</div>
            <label className="dropzone" data-over={over}
              onDragOver={(e) => (e.preventDefault(), setOver(true))}
              onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); upload(e.dataTransfer.files[0]); }}>
              <input ref={file} type="file" accept=".pdf,.xlsx,.csv" hidden onChange={(e) => upload(e.target.files?.[0])} />
              {busy === "upload" ? <span className="spinner" aria-hidden /> : <FileUp size={26} aria-hidden />}
              <span style={{ fontWeight: 600 }}>{busy === "upload" ? "Reading and checking…" : "Drop a PDF, Excel or CSV invoice here"}</span>
              <span className="hint">or click to choose a file · up to 4 MB</span>
            </label>
            <p className="hint" style={{ marginTop: 10 }}>
              Tip: download any invoice from the review page and upload it here. It will be caught as a duplicate.
            </p>
          </section>
        </div>

        <section aria-live="polite" ref={resultRef} className="lab-result">
          {error && <p className="error-box" role="alert">{error}</p>}
          {outcome && ws ? (
            <Result c={outcome} ws={ws} />
          ) : (
            !error && (
              <div className="card">
                <Empty icon={FlaskConical} title="Your result will appear here">
                  <p className="small" style={{ maxWidth: 360 }}>
                    Pick a supplier and a mistake, then press the orange button. You&rsquo;ll see whether the mistake was
                    caught, in plain words.
                  </p>
                </Empty>
              </div>
            )
          )}
        </section>
      </div>
    </div>
  );
}
