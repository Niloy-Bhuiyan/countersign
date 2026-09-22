/**
 * Plain language for everything the system says.
 *
 * The checks speak in rules and figures ("robust z 37.24 exceeds 3.5"), which is right
 * for an audit trail and useless to someone opening the page for the first time. Every
 * word a person reads first comes from here; the technical wording is still one click
 * away under "Show the details".
 */

import { money, quantity } from "./format";

export type Tone = "ok" | "warn" | "bad" | "info" | "muted";

export type Result = {
  check_code: string;
  outcome: "passed" | "failed" | "abstained";
  rule: string;
  line_no: number | null;
  observed: string | null;
  expected: string | null;
  tolerance: string | null;
  explanation: string;
  evidence: Record<string, string[]>;
};

/* ---------- the four checks ---------- */

export const CHECKS: Record<string, { name: string; question: string; plain: string }> = {
  THREE_WAY_MATCH: {
    name: "Matches the order and delivery",
    question: "Did we order this, did it arrive, and is the price what we agreed?",
    plain:
      "Compares the invoice with the purchase order (what was agreed) and the delivery note (what actually arrived). Called a three-way match.",
  },
  PRICE_VARIANCE: {
    name: "Price is normal for this supplier",
    question: "Is this price unusually high compared with what they normally charge?",
    plain:
      "Looks at the prices this supplier charged for the same item before. Flags a price only if it is both unusually high and at least 10% above normal.",
  },
  DUPLICATE_INVOICE: {
    name: "Not a duplicate",
    question: "Have we already received this invoice?",
    plain:
      "Checks for the same file, the same invoice number from the same supplier, or the same amount billed twice for one order.",
  },
  TAX_ARITHMETIC: {
    name: "VAT adds up",
    question: "Is the tax calculated correctly?",
    plain: "Recalculates the VAT on every line, to the exact paisa, and compares it with the VAT on the invoice.",
  },
};

export const CHECK_ORDER = ["THREE_WAY_MATCH", "PRICE_VARIANCE", "DUPLICATE_INVOICE", "TAX_ARITHMETIC"];

/* ---------- one finding, one sentence ---------- */

function pctAbove(observed: string | null, expected: string | null): string {
  if (!observed || !expected || Number(expected) === 0) return "";
  const pct = ((Number(observed) - Number(expected)) / Number(expected)) * 100;
  return `${Math.round(pct)}%`;
}

export function findingSentence(r: Result): string {
  const line = r.line_no ? `Line ${r.line_no}: ` : "";
  const o = r.observed;
  const e = r.expected;
  switch (`${r.check_code}/${r.rule}`) {
    case "THREE_WAY_MATCH/price_above_order":
      return `${line}the supplier charged ${money(o)} per unit, but the purchase order agreed ${money(e)} (${pctAbove(o, e)} more).`;
    case "THREE_WAY_MATCH/quantity_over_received":
      return `${line}billed for ${quantity(o)} units, but only ${quantity(e)} were delivered and not already billed.`;
    case "THREE_WAY_MATCH/no_delivery":
      return "There is no delivery note for this order, so we can't confirm the goods arrived.";
    case "THREE_WAY_MATCH/currency":
      return "The invoice is in a different currency from the purchase order.";
    case "THREE_WAY_MATCH/po_not_found":
      return "The purchase order this invoice refers to doesn't exist in our records.";
    case "THREE_WAY_MATCH/po_other_vendor":
      return "The purchase order it refers to belongs to a different supplier.";
    case "THREE_WAY_MATCH/line_unmatched":
      return `${line}this item isn't on the purchase order.`;
    case "THREE_WAY_MATCH/order_has_unread_document":
      return "Another invoice for the same order couldn't be read, so we can't be sure what's already been billed.";
    case "PRICE_VARIANCE/above_history":
      return `${line}the price ${money(o)} is about ${pctAbove(o, e)} higher than this supplier's usual ${money(e)}.`;
    case "PRICE_VARIANCE/insufficient_history":
      return `${line}we don't have enough past prices from this supplier to tell whether this price is normal.`;
    case "PRICE_VARIANCE/zero_spread":
      return `${line}this supplier has always charged exactly the same price, so there's nothing to compare against.`;
    case "PRICE_VARIANCE/no_order":
      return "Without a purchase order we can't look up the supplier's past prices.";
    case "DUPLICATE_INVOICE/same_number":
      return "This supplier already sent an invoice with the same number. It looks like a copy.";
    case "DUPLICATE_INVOICE/same_bytes":
      return "We've received this exact same file before.";
    case "DUPLICATE_INVOICE/same_order_same_amount":
      return "Another invoice already billed the same amount for the same order. It may be billed twice.";
    case "TAX_ARITHMETIC/tax_total":
      return `The invoice says VAT is ${money(o)}, but it should be ${money(e)}.`;
    case "TAX_ARITHMETIC/no_rate":
      return `${line}there's no tax rate to recalculate the VAT with.`;
    default:
      return r.explanation;
  }
}

export function passSentence(code: string): string {
  return {
    THREE_WAY_MATCH: "Quantities and prices match the purchase order and what was delivered.",
    PRICE_VARIANCE: "Prices are in line with what this supplier normally charges.",
    DUPLICATE_INVOICE: "We haven't seen this invoice before.",
    TAX_ARITHMETIC: "The VAT is calculated correctly.",
  }[code] ?? "Passed.";
}

/** Short, list-sized version of the most important thing about an invoice. */
export function shortIssue(failed: string[], abstained: string[], reason: string | null): string {
  if (reason && reason !== "check_findings") return REASONS[reason]?.short ?? reason;
  const key = failed[0] ?? abstained[0];
  if (!key) return "All checks passed";
  const extra = failed.length > 1 ? ` + ${failed.length - 1} more` : "";
  return (SHORT[key] ?? key) + extra;
}

const SHORT: Record<string, string> = {
  "THREE_WAY_MATCH/price_above_order": "Charged more than agreed",
  "THREE_WAY_MATCH/quantity_over_received": "Billed more than delivered",
  "THREE_WAY_MATCH/no_delivery": "No delivery on record",
  "THREE_WAY_MATCH/currency": "Wrong currency",
  "THREE_WAY_MATCH/po_not_found": "Unknown purchase order",
  "THREE_WAY_MATCH/po_other_vendor": "Order is another supplier's",
  "THREE_WAY_MATCH/line_unmatched": "Item not on the order",
  "THREE_WAY_MATCH/order_has_unread_document": "Related invoice unreadable",
  "PRICE_VARIANCE/above_history": "Price much higher than usual",
  "PRICE_VARIANCE/insufficient_history": "Not enough price history",
  "PRICE_VARIANCE/zero_spread": "No price history to compare",
  "PRICE_VARIANCE/no_order": "No order to compare with",
  "DUPLICATE_INVOICE/same_number": "Possible duplicate",
  "DUPLICATE_INVOICE/same_bytes": "Same file sent twice",
  "DUPLICATE_INVOICE/same_order_same_amount": "May be billed twice",
  "TAX_ARITHMETIC/tax_total": "VAT is wrong",
  "TAX_ARITHMETIC/no_rate": "No tax rate",
};

export function shortLabel(key: string): string {
  return SHORT[key] ?? key;
}

/* ---------- why an invoice skipped the checks ---------- */

export const REASONS: Record<string, { short: string; long: string }> = {
  extraction_failed: {
    short: "Couldn't read it reliably",
    long: "We read the document, but the numbers didn't add up (for example, the lines don't sum to the subtotal), so we didn't trust the result. A person needs to check it.",
  },
  quarantined_image_only: {
    short: "Scanned image, no text",
    long: "This is a scanned picture with no text inside, so it can't be read automatically.",
  },
  quarantined_unreadable: { short: "File is damaged", long: "The file is corrupt and couldn't be opened." },
  quarantined_encrypted: { short: "Password protected", long: "The supplier password-protected this file, so it couldn't be opened." },
  vendor_not_on_master: { short: "Unknown supplier", long: "This supplier isn't in our list of approved suppliers." },
  vendor_ambiguous: { short: "Supplier unclear", long: "Two suppliers have similar names and the invoice doesn't say which one it is." },
  vendor_tax_id_mismatch: { short: "Tax ID doesn't match", long: "The tax ID on the invoice doesn't match the supplier's name." },
};

/* ---------- overall status ---------- */

export type Status = { label: string; tone: Tone; help: string };

export function statusOf(
  row: { state: string; failed: string[]; abstained: string[]; reason: string | null },
  decision?: string,
): Status {
  if (decision === "approved") return { label: "Approved", tone: "ok", help: "A person approved this for payment." };
  if (decision === "held") return { label: "On hold", tone: "warn", help: "A person put this on hold." };
  if (decision === "escalated") return { label: "Escalated", tone: "bad", help: "A person sent this to the finance controller." };
  if (row.state === "cleared")
    return { label: "Ready to pay", tone: "ok", help: "Passed all four checks. Still needs a person to approve it." };
  if (row.reason && row.reason !== "check_findings")
    return { label: "Can't read", tone: "warn", help: "The document couldn't be read, so no checks ran." };
  if (row.failed.length) return { label: "Problem found", tone: "bad", help: "At least one check failed." };
  return { label: "Needs a look", tone: "warn", help: "No check failed, but at least one couldn't decide." };
}

/* ---------- what to do next ---------- */

export const NEXT_STEP: Record<string, { what: string; why: string; tone: Tone }> = {
  CLEAR_FOR_PAYMENT: {
    what: "Approve for payment",
    why: "Everything checks out. Approving it is the only step left.",
    tone: "ok",
  },
  HOLD_REQUEST_CREDIT_NOTE: {
    what: "Hold it and ask the supplier for a credit note",
    why: "They charged too much. A credit note is the supplier's correction for the difference.",
    tone: "warn",
  },
  HOLD_REQUEST_DELIVERY_PROOF: {
    what: "Hold it and ask for proof of delivery",
    why: "We're being billed for goods we have no record of receiving.",
    tone: "warn",
  },
  ESCALATE_TO_CONTROLLER: {
    what: "Escalate to the finance controller",
    why: "This looks like more than a simple mistake, such as a duplicate or an unusual price, so someone senior should look.",
    tone: "bad",
  },
  REVIEW_MANUALLY: {
    what: "Check it yourself",
    why: "The system couldn't decide on its own, so it's asking a person to look.",
    tone: "muted",
  },
};

/* ---------- glossary ---------- */

export const TERMS: { term: string; means: string }[] = [
  { term: "Invoice", means: "The bill a supplier sends asking to be paid." },
  { term: "Purchase order (PO)", means: "Our own record of what we agreed to buy: which items, how many, and at what price. The supplier never edits it." },
  { term: "Delivery note", means: "Our record of what actually arrived at the warehouse." },
  { term: "Three-way match", means: "Checking that the invoice, the purchase order and the delivery note all agree." },
  { term: "Price history", means: "The prices this supplier charged us for the same item on earlier orders." },
  { term: "Duplicate", means: "The same invoice sent twice, which could lead to paying twice." },
  { term: "VAT", means: "Value-added tax, shown separately on each invoice." },
  { term: "Credit note", means: "A document from the supplier that reduces what we owe, used to correct an overcharge." },
  { term: "Ready to pay", means: "Passed every check. It still waits for a person to approve it; nothing is paid automatically." },
  { term: "Needs a look", means: "Nothing failed, but a check couldn't decide, for example because there's too little price history." },
  { term: "On hold / Escalated", means: "Decisions a person made. On hold means waiting for the supplier; escalated means sent to a senior person." },
  { term: "Workspace", means: "Your own private space in this demo. Your uploads and decisions are saved here, under your link." },
  { term: "Synthetic data", means: "Every supplier, invoice and amount here is made up for the demo. No real company is involved." },
];
