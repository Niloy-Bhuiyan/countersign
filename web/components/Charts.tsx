/**
 * Two chart forms, drawn as plain SVG and HTML so they follow the theme tokens.
 * Bar lengths are scaled with Number() because they are geometry, not money; every
 * amount printed beside a bar is the exact decimal string.
 */

import { compact, money } from "./format";

export type Datum = { label: string; value: string | number };

function magnitude(value: string | number): number {
  return typeof value === "number" ? value : Number(value);
}

export function HBars({
  data,
  format = "money",
  labelFor = (label: string) => label,
}: {
  data: Datum[];
  format?: "money" | "count";
  labelFor?: (label: string) => string;
}) {
  const max = Math.max(...data.map((d) => magnitude(d.value)), 1);
  return (
    <div role="list">
      {data.map((d) => {
        const width = (magnitude(d.value) / max) * 100;
        const printed = format === "money" ? money(String(d.value)) : String(d.value);
        return (
          <div className="hbar" role="listitem" key={d.label} aria-label={`${labelFor(d.label)}: ${printed}`}>
            <span className="label" title={labelFor(d.label)}>
              {labelFor(d.label)}
            </span>
            <span className="track" aria-hidden="true">
              <span className="fill" style={{ width: `${width}%`, display: "block" }} />
            </span>
            <span className="num small">{printed}</span>
          </div>
        );
      })}
    </div>
  );
}

export function Columns({ data }: { data: { period: string; value: string }[] }) {
  const width = 720;
  const height = 200;
  const pad = { top: 12, right: 8, bottom: 26, left: 56 };
  const max = Math.max(...data.map((d) => Number(d.value)), 1);
  const band = (width - pad.left - pad.right) / Math.max(data.length, 1);
  const y = (v: number) => pad.top + (height - pad.top - pad.bottom) * (1 - v / max);
  const ticks = [0, 0.5, 1].map((t) => t * max);

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      role="img"
      aria-label={`Invoiced value by month, ${data.length} months`}
    >
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} stroke="var(--line)" />
          <text x={pad.left - 8} y={y(t) + 4} textAnchor="end">
            {compact(String(Math.round(t)))}
          </text>
        </g>
      ))}
      {data.map((d, i) => {
        const x = pad.left + i * band + band * 0.18;
        const top = y(Number(d.value));
        return (
          <g key={d.period}>
            <rect x={x} y={top} width={band * 0.64} height={height - pad.bottom - top} fill="var(--bar)">
              <title>{`${d.period}: ${money(d.value)} BDT`}</title>
            </rect>
            {i % 2 === 0 && (
              <text x={x + band * 0.32} y={height - 8} textAnchor="middle">
                {d.period.slice(2).replace("-", "/")}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
