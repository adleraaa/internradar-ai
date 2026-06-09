import type { Internship } from "./types";

// A free-text note conveys no definite information when it is empty, literally
// "Unclear", or a "not stated / not explicitly stated" phrasing.
export function isUnclearText(value: string | undefined | null): boolean {
  const text = (value ?? "").trim().toLowerCase();
  if (!text) return true;
  return (
    text === "unclear" ||
    text.startsWith("unclear") ||
    text.includes("not stated") ||
    text.includes("not explicitly")
  );
}

export interface SummaryStats {
  total: number;
  open: number;
  aiRelevant: number;
  fullStackRelevant: number;
  citizenshipRestricted: number;
  unclearWorkAuth: number;
  knownComp: number;
  unclearComp: number;
}

// Compensation is "known" when compensation_note is present and not "Unclear".
export function hasKnownComp(d: { compensation_note?: string }): boolean {
  const note = (d.compensation_note ?? "").trim();
  return note !== "" && note.toLowerCase() !== "unclear";
}

// Format a USD amount with thousands separators, trimming decimal noise:
// 50 -> "50", 7000 -> "7,000", 50.5 -> "50.50".
function formatAmount(n: number): string {
  const isInt = Number.isInteger(n);
  return n.toLocaleString("en-US", {
    minimumFractionDigits: isInt ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

// Build a compact, clearly-united pay string from the structured compensation
// fields (period + min/max), falling back to compensation_note. Display only —
// never mutates the dataset.
export function formatCompensation(d: Internship): string {
  const period = d.compensation_period;
  const note = (d.compensation_note ?? "").trim();
  const min = d.compensation_min;
  const max = d.compensation_max;
  const cur = d.compensation_currency === "USD" ? "$" : "";
  const noteFallback = () =>
    note && note.toLowerCase() !== "unclear" ? note : "Unclear";

  if (period === "Unclear") return noteFallback();
  if (period === "Unpaid") return "Unpaid";
  if (period === "Other") return note || "Other";

  const suffix =
    period === "Hour" ? "/hr" :
    period === "Month" ? "/month" :
    period === "Year" ? "/year" :
    period === "Stipend" ? " stipend" : "";

  if (typeof min === "number" && typeof max === "number") {
    const value =
      min === max
        ? `${cur}${formatAmount(min)}`
        : `${cur}${formatAmount(min)} - ${cur}${formatAmount(max)}`;
    return `${value}${suffix}`;
  }
  const single = typeof min === "number" ? min : typeof max === "number" ? max : null;
  if (single !== null) return `${cur}${formatAmount(single)}${suffix}`;

  return noteFallback();
}

export function computeSummary(data: Internship[]): SummaryStats {
  const relevant = (r: string) => r === "High" || r === "Medium";
  return {
    total: data.length,
    open: data.filter((d) => d.status === "Open").length,
    aiRelevant: data.filter((d) => relevant(d.ai_relevance)).length,
    fullStackRelevant: data.filter((d) => relevant(d.full_stack_relevance)).length,
    citizenshipRestricted: data.filter((d) => d.requires_us_citizenship === "Yes").length,
    unclearWorkAuth: data.filter(
      (d) => isUnclearText(d.sponsorship_note) || isUnclearText(d.work_authorization_note),
    ).length,
    knownComp: data.filter((d) => hasKnownComp(d)).length,
    unclearComp: data.filter((d) => !hasKnownComp(d)).length,
  };
}

// Unique, sorted list of a string field's values, for building filter options.
export function uniqueValues(data: Internship[], key: keyof Internship): string[] {
  const set = new Set<string>();
  for (const d of data) {
    const v = d[key];
    if (typeof v === "string" && v.trim()) set.add(v);
  }
  return Array.from(set).sort();
}
