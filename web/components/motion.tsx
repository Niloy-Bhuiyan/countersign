"use client";

/**
 * Countersign's signature touches: the ink stamp, the pen stroke, and numbers that count
 * up. Every animation starts from its final state in CSS, so with reduced motion the
 * page simply shows the end result.
 */

import { useEffect, useId, useRef, useState } from "react";

const INK = { ok: "#15803d", warn: "#b45309", bad: "#b91c1c", paper: "#ffffff" };

/** A rubber stamp with worn ink. Decorative: the same status is always written in words nearby. */
export function Stamp({ word, tone, size = 104, className = "" }: {
  word: string;
  tone: keyof typeof INK;
  size?: number;
  className?: string;
}) {
  const id = `ink${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const colour = INK[tone];
  return (
    <svg className={`stamp ${className}`} width={size} height={size} viewBox="0 0 120 120" aria-hidden
      style={{ color: colour }}>
      <defs>
        <filter id={id}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" result="noise" />
          <feColorMatrix in="noise" type="matrix" result="wear"
            values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1.5 0 0 0 1.8" />
          <feComposite in="SourceGraphic" in2="wear" operator="in" />
        </filter>
        <path id={`${id}arc`} d="M 22 60 A 38 38 0 0 1 98 60" />
      </defs>
      <g filter={`url(#${id})`} fill="none" stroke="currentColor">
        <circle cx="60" cy="60" r="54" strokeWidth="4" />
        <circle cx="60" cy="60" r="47" strokeWidth="1.4" />
        <text fill="currentColor" stroke="none" fontSize="10" fontWeight="700" letterSpacing="3.2">
          <textPath href={`#${id}arc`} startOffset="50%" textAnchor="middle">COUNTERSIGN</textPath>
        </text>
        <line x1="24" x2="96" y1="66" y2="66" strokeWidth="1.4" />
        <text x="60" y="84" fill="currentColor" stroke="none" fontSize={word.length > 8 ? 12 : 15}
          fontWeight="800" letterSpacing="1.5" textAnchor="middle">{word}</text>
      </g>
    </svg>
  );
}

/** A handwritten stroke that draws itself, like a signature on the line. */
export function PenStroke({ className = "" }: { className?: string }) {
  return (
    <svg className={`pen ${className}`} viewBox="0 0 220 40" preserveAspectRatio="none" aria-hidden>
      <path d="M4 26 C 26 12, 40 34, 62 22 S 96 6, 112 22 S 138 36, 156 20 C 166 12, 176 10, 180 18 C 184 26, 170 30, 172 22 C 176 12, 200 14, 216 10"
        pathLength={1} />
    </svg>
  );
}

/** True once the element has been on screen; used to start an animation when seen. */
export function useSeen<T extends Element>() {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setSeen(true), { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, [seen]);
  return { ref, seen };
}

/** Counts the first number in `text` up from zero once it is on screen, keeping the rest as written. */
export function CountUp({ text }: { text: string }) {
  const { ref, seen } = useSeen<HTMLSpanElement>();
  const match = text.match(/\d+(?:\.\d+)?/);
  const [shown, setShown] = useState(text);

  useEffect(() => {
    if (!match || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return setShown(text);
    const target = Number(match[0]);
    const decimals = match[0].split(".")[1]?.length ?? 0;
    if (!seen) return setShown(text.replace(match[0], (0).toFixed(decimals)));
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / 1100, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(text.replace(match[0], (target * eased).toFixed(decimals)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seen, text]);

  return <span ref={ref}>{shown}</span>;
}
