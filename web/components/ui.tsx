"use client";

import { AlertTriangle, CheckCircle2, CircleHelp, Info, XCircle } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { Status, Tone } from "./explain";

const TONE_ICON = { ok: CheckCircle2, warn: AlertTriangle, bad: XCircle, info: Info, muted: CircleHelp };

/** Status as a pill: icon plus word, colour secondary. Never wraps. */
export function Pill({ tone, children, icon = true }: { tone: Tone; children: React.ReactNode; icon?: boolean }) {
  const Icon = TONE_ICON[tone];
  return (
    <span className={`pill pill-${tone}`}>
      {icon && <Icon size={13} aria-hidden />}
      {children}
    </span>
  );
}

export function StatusPill({ status }: { status: Status }) {
  return (
    <span title={status.help}>
      <Pill tone={status.tone}>{status.label}</Pill>
    </span>
  );
}

/**
 * An explanation behind a small info button. Opens on click, tap or keyboard, closes on
 * Escape or a click elsewhere; never hover-only, so it works on touch screens.
 */
export function Tip({ children, label = "What does this mean?" }: { children: React.ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const box = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <span className="tip" ref={box}>
      <button type="button" className="tip-btn" aria-label={label} aria-expanded={open} aria-controls={id}
        onClick={() => setOpen((v) => !v)}>
        <Info size={15} aria-hidden />
      </button>
      {open && (
        <span className="tip-box" id={id} role="note">
          {children}
        </span>
      )}
    </span>
  );
}

export function Empty({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children?: React.ReactNode }) {
  return (
    <div className="empty">
      <span className="ic"><Icon size={24} aria-hidden /></span>
      <h3>{title}</h3>
      {children}
    </div>
  );
}
