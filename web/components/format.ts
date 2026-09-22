/**
 * Display formatting. Amounts arrive as decimal strings and are grouped as strings,
 * so the console never routes a figure through a binary float on its way to the screen.
 */

export function money(value: string | null | undefined, currency?: string | null): string {
  if (value === null || value === undefined) return "—";
  const negative = value.startsWith("-");
  const [whole, fraction = "00"] = value.replace("-", "").split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const text = `${negative ? "-" : ""}${grouped}.${fraction.padEnd(2, "0").slice(0, 2)}`;
  return currency ? `${text} ${currency}` : text;
}

/** Compact form for dashboard headlines: 910,791,525.78 -> 910.8M */
export function compact(value: string): string {
  const whole = value.split(".")[0].replace("-", "");
  const digits = whole.length;
  if (digits > 9) return `${whole.slice(0, digits - 9)}.${whole.slice(digits - 9, digits - 8)}B`;
  if (digits > 6) return `${whole.slice(0, digits - 6)}.${whole.slice(digits - 6, digits - 5)}M`;
  if (digits > 3) return `${whole.slice(0, digits - 3)}.${whole.slice(digits - 3, digits - 2)}K`;
  return whole;
}

export function quantity(value: string | null): string {
  if (value === null) return "—";
  const [whole, fraction] = value.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return fraction && /[1-9]/.test(fraction) ? `${grouped}.${fraction.replace(/0+$/, "")}` : grouped;
}

export function date(value: string | null): string {
  if (!value) return "—";
  const [y, m, d] = value.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${d} ${months[Number(m) - 1]} ${y}`;
}

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "n/a";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Sort key for decimal strings without parsing them as floats. */
export function compareDecimal(a: string | null, b: string | null): number {
  if (a === b) return 0;
  if (a === null) return -1;
  if (b === null) return 1;
  const [aw, af = ""] = a.split(".");
  const [bw, bf = ""] = b.split(".");
  if (aw.length !== bw.length) return aw.length - bw.length;
  if (aw !== bw) return aw < bw ? -1 : 1;
  const width = Math.max(af.length, bf.length);
  const x = af.padEnd(width, "0");
  const y = bf.padEnd(width, "0");
  return x === y ? 0 : x < y ? -1 : 1;
}
