import type { ReactNode } from "react";

export type Tone = "green" | "red" | "amber" | "blue" | "slate";

const TONES: Record<Tone, string> = {
  green: "bg-green-100 text-green-800 ring-green-600/20",
  red: "bg-red-100 text-red-800 ring-red-600/20",
  amber: "bg-amber-100 text-amber-800 ring-amber-600/20",
  blue: "bg-blue-100 text-blue-800 ring-blue-600/20",
  slate: "bg-slate-100 text-slate-700 ring-slate-500/20",
};

export function Badge({
  children,
  tone = "slate",
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function statusTone(status: string): Tone {
  if (status === "Open") return "green";
  if (status === "Closed") return "red";
  return "amber";
}

export function relevanceTone(rel: string): Tone {
  if (rel === "High") return "green";
  if (rel === "Medium") return "blue";
  if (rel === "Low") return "slate";
  if (rel === "None") return "slate";
  return "amber";
}

export function citizenshipTone(value: string): Tone {
  // "Yes" = citizenship required (restrictive) -> red; "No" -> green; else amber.
  if (value === "Yes") return "red";
  if (value === "No") return "green";
  return "amber";
}
