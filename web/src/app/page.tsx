import { internships } from "@/lib/data";
import { computeSummary } from "@/lib/util";
import { SummaryCards } from "@/components/SummaryCards";
import { Dashboard } from "@/components/Dashboard";

export default function Home() {
  const data = internships;
  const stats = computeSummary(data);

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          InternRadar AI
        </h1>
        <p className="mt-2 text-base text-slate-600">
          Verified internship listings for undergraduate CS students.
        </p>
      </header>

      <SummaryCards stats={stats} />

      <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <strong>Data freshness:</strong> entries are point-in-time snapshots with a{" "}
        last-verified date. Always re-check the official company page before applying.
      </div>

      <Dashboard data={data} />

      <footer className="mt-12 border-t border-slate-200 pt-6 text-xs text-slate-400">
        InternRadar AI is an aid, not an authority. The source of truth is{" "}
        <code>data/internships.json</code> in the repository root. This dashboard is a
        read-only view and never applies to jobs on your behalf.
      </footer>
    </main>
  );
}
