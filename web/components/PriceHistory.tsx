import { money } from "./format";

export type History = {
  lineNo: number;
  sku: string;
  billed: string;
  points: { po: string; date: string; price: string }[];
  median: string | null;
  mad: string | null;
  minPoints: number;
  materialPct: string;
};

const Z = 3.5;
const CONSISTENCY = 0.6745;

/**
 * What the price-variance check saw: this vendor's earlier prices for the item, their
 * median, and the line a price has to cross to fail — above both the robust z-score
 * threshold and the materiality floor. Geometry uses Number(); every printed figure is
 * the exact decimal string.
 */
export default function PriceHistory({ h }: { h: History }) {
  const prices = h.points.map((p) => Number(p.price));
  const billed = Number(h.billed);
  const width = 640;
  const height = 132;
  const pad = { l: 64, r: 96, t: 14, b: 22 };

  if (prices.length < h.minPoints || h.median === null || h.mad === null) {
    return (
      <p className="small muted">
        {h.sku}: {h.points.length} earlier price{h.points.length === 1 ? "" : "s"} from this vendor, fewer than the{" "}
        {h.minPoints} needed. The check abstained rather than judge on too little.
      </p>
    );
  }

  const median = Number(h.median);
  const mad = Number(h.mad);
  const zLine = mad > 0 ? median + (Z * mad) / CONSISTENCY : median;
  const floor = median * (1 + Number(h.materialPct) / 100);
  const failAbove = Math.max(zLine, floor);
  const lo = Math.min(...prices, billed, median) * 0.97;
  const hi = Math.max(...prices, billed, failAbove) * 1.03;
  const y = (v: number) => pad.t + (height - pad.t - pad.b) * (1 - (v - lo) / (hi - lo));
  const x = (i: number) => pad.l + ((width - pad.l - pad.r) * i) / Math.max(prices.length, 1);
  const flagged = billed > failAbove;
  const bx = x(prices.length);

  return (
    <figure style={{ margin: 0 }}>
      <svg className="chart" viewBox={`0 0 ${width} ${height}`} width="100%" role="img"
        aria-label={`${h.sku}: billed ${h.billed} against a median of ${money(h.median)} over ${prices.length} earlier orders; fails above ${failAbove.toFixed(2)}`}>
        <rect x={pad.l} y={pad.t} width={width - pad.l - pad.r} height={Math.max(0, y(failAbove) - pad.t)} fill="var(--red-wash)" />
        <line x1={pad.l} x2={width - pad.r} y1={y(failAbove)} y2={y(failAbove)} stroke="var(--red)" strokeDasharray="3 3" />
        <line x1={pad.l} x2={width - pad.r} y1={y(median)} y2={y(median)} stroke="var(--ink-3)" />
        <text x={pad.l - 8} y={y(median) + 4} textAnchor="end">{money(h.median)}</text>
        <text x={pad.l - 8} y={y(failAbove) + 4} textAnchor="end" style={{ fill: "var(--red)" }}>
          {money(failAbove.toFixed(2))}
        </text>
        {h.points.map((p, i) => (
          <circle key={p.po + i} cx={x(i)} cy={y(Number(p.price))} r={3} fill="var(--ink)">
            <title>{`${p.po}, ${p.date}: ${money(p.price)}`}</title>
          </circle>
        ))}
        <line x1={bx} x2={bx} y1={pad.t} y2={height - pad.b} stroke="var(--rule-strong)" />
        {flagged ? (
          <path d={`M${bx} ${y(billed) - 6} L${bx + 6} ${y(billed)} L${bx} ${y(billed) + 6} L${bx - 6} ${y(billed)} Z`} fill="var(--red)" />
        ) : (
          <circle cx={bx} cy={y(billed)} r={5} fill="var(--sheet)" stroke="var(--ink)" strokeWidth={2} />
        )}
        <text x={bx + 12} y={y(billed) + 4} style={{ fill: flagged ? "var(--red)" : "var(--ink)", fontWeight: 600 }}>
          {money(h.billed)}
        </text>
        <text x={pad.l} y={height - 6}>{h.points[0]?.date}</text>
        <text x={bx} y={height - 6} textAnchor="middle">this invoice</text>
      </svg>
      <figcaption className="small muted">
        {h.sku}, line {h.lineNo}: {prices.length} earlier orders. Median {money(h.median)}; a price fails above{" "}
        {money(failAbove.toFixed(2))}, the higher of the robust z {Z} line and the {h.materialPct}% materiality floor.
      </figcaption>
    </figure>
  );
}
