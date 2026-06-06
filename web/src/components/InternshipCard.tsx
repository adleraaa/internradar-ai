import type { Internship } from "@/lib/types";
import {
  Badge,
  citizenshipTone,
  relevanceTone,
  statusTone,
} from "./Badge";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm text-slate-700">{children}</dd>
    </div>
  );
}

export function InternshipCard({ item }: { item: Internship }) {
  return (
    <article className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{item.company}</h3>
          <p className="text-sm text-slate-600">{item.role}</p>
        </div>
        <Badge tone={statusTone(item.status)}>{item.status}</Badge>
      </header>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge tone="slate">{item.category}</Badge>
        <Badge tone="slate">{item.location_type}</Badge>
        {item.internship_term ? <Badge tone="slate">{item.internship_term}</Badge> : null}
        <Badge tone={relevanceTone(item.ai_relevance)} title="AI relevance">
          AI: {item.ai_relevance}
        </Badge>
        <Badge tone={relevanceTone(item.full_stack_relevance)} title="Full-stack relevance">
          FS: {item.full_stack_relevance}
        </Badge>
        <Badge tone={citizenshipTone(item.requires_us_citizenship)} title="Requires U.S. citizenship">
          Citizenship: {item.requires_us_citizenship}
        </Badge>
        {(() => {
          const note = (item.compensation_note || "").trim();
          const known = note !== "" && note.toLowerCase() !== "unclear";
          return (
            <Badge tone={known ? "green" : "slate"} title="Pay (official page only)">
              Pay: {known ? note : "Unclear"}
            </Badge>
          );
        })()}
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3">
        <Field label="Pay">{item.compensation_note || "Unclear"}</Field>
        <Field label="Location">{item.location || "—"}</Field>
        <Field label="Student level">{item.student_level}</Field>
        <Field label="Last verified">{item.last_verified_date}</Field>
        <Field label="Freshman/Soph friendly">{item.freshman_sophomore_friendly}</Field>
      </dl>

      {item.tech_keywords.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {item.tech_keywords.map((kw) => (
            <Badge key={kw} tone="blue">
              {kw}
            </Badge>
          ))}
        </div>
      )}

      <dl className="mt-4 space-y-3 border-t border-slate-100 pt-4">
        <Field label="Sponsorship note">{item.sponsorship_note || "—"}</Field>
        <Field label="Work authorization note">{item.work_authorization_note || "—"}</Field>
        <Field label="Fit summary">{item.fit_summary || "—"}</Field>
        {item.risk_flags.length > 0 && (
          <Field label="Risk flags">
            <div className="flex flex-wrap gap-1.5">
              {item.risk_flags.map((flag) => (
                <Badge key={flag} tone="amber">
                  {flag}
                </Badge>
              ))}
            </div>
          </Field>
        )}
      </dl>

      <div className="mt-5 flex items-center justify-between gap-3">
        <span className="text-xs text-slate-400">{item.source_type}</span>
        <a
          href={item.application_url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Apply to ${item.role} at ${item.company} — opens the official application page in a new tab`}
          className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-700"
        >
          Apply →
        </a>
      </div>

      <p className="mt-3 text-[11px] leading-snug text-slate-400">
        Re-check the official page before applying — status and eligibility can
        change after the last-verified date.
      </p>
    </article>
  );
}
