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
