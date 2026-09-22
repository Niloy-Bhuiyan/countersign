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
 * This supplier's past prices for the item, the usual price, and the line a price has
 * to cross to be flagged, with this invoice's price marked. A legend and a sentence
 * say the same thing in words, so the chart never has to be decoded.
 */
export default function PriceHistory({ h, description }: { h: History; description: string }) {
  const prices = h.points.map((p) => Number(p.price));
  const billed = Number(h.billed);

  if (prices.length < h.minPoints || h.median === null || h.mad === null) {
    return (
      <p className="small soft">
        <b>{description}:</b> only {h.points.length} earlier price{h.points.length === 1 ? "" : "s"} from this supplier.
        At least {h.minPoints} are needed to say what&rsquo;s normal, so this check couldn&rsquo;t decide.
      </p>
    );
  }

  const width = 640;
  const height = 150;
  const pad = { l: 70, r: 110, t: 16, b: 26 };
  const median = Number(h.median);
  const mad = Number(h.mad);
  const zLine = mad > 0 ? median + (Z * mad) / CONSISTENCY : median;
  const limit = Math.max(zLine, median * (1 + Number(h.materialPct) / 100));
  const lo = Math.min(...prices, billed, median) * 0.96;
  const hi = Math.max(...prices, billed, limit) * 1.04;
  const y = (v: number) => pad.t + (height - pad.t - pad.b) * (1 - (v - lo) / (hi - lo));
  const x = (i: number) => pad.l + ((width - pad.l - pad.r) * i) / Math.max(prices.length, 1);
  const flagged = billed > limit;
  const bx = x(prices.length);
  const pct = Math.round(((billed - median) / median) * 100);

  return (
    <figure style={{ margin: 0 }}>
      <p className="small" style={{ fontWeight: 700, marginBottom: 4 }}>{description}</p>
      <svg className="chart" viewBox={`0 0 ${width} ${height}`} width="100%" role="img"
        aria-label={`${description}: charged ${money(h.billed)}; usual price ${money(h.median)}; flagged above ${money(limit.toFixed(2))}.`}>
        <rect x={pad.l} y={pad.t} width={width - pad.l - pad.r} height={Math.max(0, y(limit) - pad.t)} fill="#fef2f2" />
        <line x1={pad.l} x2={width - pad.r} y1={y(limit)} y2={y(limit)} stroke="#ef4444" strokeDasharray="5 4" strokeWidth={1.5} />
        <line x1={pad.l} x2={width - pad.r} y1={y(median)} y2={y(median)} stroke="#94a3b8" strokeWidth={1.5} />
        <text x={pad.l - 8} y={y(median) + 4} textAnchor="end">{money(h.median)}</text>
        <text x={pad.l - 8} y={y(limit) + 4} textAnchor="end" style={{ fill: "#b91c1c" }}>{money(limit.toFixed(2))}</text>
        {h.points.map((p, i) => (
          <circle key={p.po + i} cx={x(i)} cy={y(Number(p.price))} r={4.5} fill="#2563eb">
            <title>{`${p.date}: ${money(p.price)}`}</title>
          </circle>
        ))}
        <circle cx={bx} cy={y(billed)} r={7} fill={flagged ? "#dc2626" : "#16a34a"} stroke="#fff" strokeWidth={2} />
        <text x={bx + 13} y={y(billed) + 4} style={{ fill: flagged ? "#b91c1c" : "#15803d", fontWeight: 700 }}>
          {money(h.billed)}
        </text>
        <text x={pad.l} y={height - 6}>{h.points[0]?.date}</text>
        <text x={bx} y={height - 6} textAnchor="middle">This invoice</text>
      </svg>
      <div className="legend">
        <span><i style={{ background: "#2563eb", borderRadius: 999 }} /> Past prices from this supplier</span>
        <span><i style={{ background: "#94a3b8", height: 3 }} /> Usual price (middle value)</span>
        <span><i style={{ background: "#ef4444", height: 3 }} /> Flagged above this line</span>
        <span><i style={{ background: flagged ? "#dc2626" : "#16a34a", borderRadius: 999 }} /> This invoice</span>
      </div>
      <p className="small soft" style={{ marginTop: 8 }}>
        {flagged
          ? `Charged ${money(h.billed)}, about ${pct}% above the usual ${money(h.median)}. That's above the red line, so it was flagged.`
          : `Charged ${money(h.billed)}, close to the usual ${money(h.median)}. That's below the red line, so the price is fine.`}
      </p>
    </figure>
  );
}
