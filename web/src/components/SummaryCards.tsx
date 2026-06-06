import type { SummaryStats } from "@/lib/util";

interface CardDef {
  label: string;
  value: number;
  hint: string;
}

export function SummaryCards({ stats }: { stats: SummaryStats }) {
  const cards: CardDef[] = [
    { label: "Verified postings", value: stats.total, hint: "Total entries in the dataset" },
    { label: "Open", value: stats.open, hint: "Status marked Open" },
    { label: "AI/ML-relevant", value: stats.aiRelevant, hint: "AI relevance High or Medium" },
    {
      label: "Full-stack-relevant",
      value: stats.fullStackRelevant,
      hint: "Full-stack relevance High or Medium",
    },
    {
      label: "Citizenship-restricted",
      value: stats.citizenshipRestricted,
      hint: "Requires U.S. citizenship = Yes",
    },
    {
      label: "Unclear sponsorship / work auth",
      value: stats.unclearWorkAuth,
      hint: "Sponsorship or work-authorization note is unclear",
    },
  ];

  return (
    <section
      aria-label="Summary"
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
    >
      {cards.map((c) => (
        <div
          key={c.label}
          title={c.hint}
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <div className="text-2xl font-semibold text-slate-900">{c.value}</div>
          <div className="mt-1 text-xs font-medium leading-tight text-slate-500">
            {c.label}
          </div>
        </div>
      ))}
    </section>
  );
}
