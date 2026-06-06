"use client";

import { useMemo, useState } from "react";
import type { Internship } from "@/lib/types";
import { uniqueValues } from "@/lib/util";
import { InternshipCard } from "./InternshipCard";

const ALL = "All";

type SortKey = "verified_desc" | "company_az" | "role_az";

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800 shadow-sm focus:border-slate-500 focus:outline-none"
      >
        {[ALL, ...options].map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Dashboard({ data }: { data: Internship[] }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(ALL);
  const [locationType, setLocationType] = useState(ALL);
  const [status, setStatus] = useState(ALL);
  const [aiRel, setAiRel] = useState(ALL);
  const [fsRel, setFsRel] = useState(ALL);
  const [citizenship, setCitizenship] = useState(ALL);
  const [freshSoph, setFreshSoph] = useState(ALL);
  const [sort, setSort] = useState<SortKey>("verified_desc");

  const options = useMemo(
    () => ({
      category: uniqueValues(data, "category"),
      locationType: uniqueValues(data, "location_type"),
      status: uniqueValues(data, "status"),
      aiRel: uniqueValues(data, "ai_relevance"),
      fsRel: uniqueValues(data, "full_stack_relevance"),
      citizenship: uniqueValues(data, "requires_us_citizenship"),
      freshSoph: uniqueValues(data, "freshman_sophomore_friendly"),
    }),
    [data],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matchAll = (v: string, sel: string) => sel === ALL || v === sel;

    const result = data.filter((d) => {
      if (q) {
        const haystack = [
          d.company,
          d.role,
          d.location,
          d.tech_keywords.join(" "),
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return (
        matchAll(d.category, category) &&
        matchAll(d.location_type, locationType) &&
        matchAll(d.status, status) &&
        matchAll(d.ai_relevance, aiRel) &&
        matchAll(d.full_stack_relevance, fsRel) &&
        matchAll(d.requires_us_citizenship, citizenship) &&
        matchAll(d.freshman_sophomore_friendly, freshSoph)
      );
    });

    const sorted = [...result];
    if (sort === "verified_desc") {
      sorted.sort(
        (a, b) =>
          b.last_verified_date.localeCompare(a.last_verified_date) ||
          a.company.localeCompare(b.company),
      );
    } else if (sort === "company_az") {
      sorted.sort(
        (a, b) => a.company.localeCompare(b.company) || a.role.localeCompare(b.role),
      );
    } else {
      sorted.sort(
        (a, b) => a.role.localeCompare(b.role) || a.company.localeCompare(b.company),
      );
    }
    return sorted;
  }, [
    data,
    search,
    category,
    locationType,
    status,
    aiRel,
    fsRel,
    citizenship,
    freshSoph,
    sort,
  ]);

  function reset() {
    setSearch("");
    setCategory(ALL);
    setLocationType(ALL);
    setStatus(ALL);
    setAiRel(ALL);
    setFsRel(ALL);
    setCitizenship(ALL);
    setFreshSoph(ALL);
    setSort("verified_desc");
  }

  return (
    <section className="mt-8">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company, role, location, or tech keyword…"
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-slate-500 focus:outline-none"
          />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8">
            <Select label="Category" value={category} options={options.category} onChange={setCategory} />
            <Select label="Location type" value={locationType} options={options.locationType} onChange={setLocationType} />
            <Select label="Status" value={status} options={options.status} onChange={setStatus} />
            <Select label="AI relevance" value={aiRel} options={options.aiRel} onChange={setAiRel} />
            <Select label="Full-stack" value={fsRel} options={options.fsRel} onChange={setFsRel} />
            <Select label="Citizenship" value={citizenship} options={options.citizenship} onChange={setCitizenship} />
            <Select label="Fresh/Soph" value={freshSoph} options={options.freshSoph} onChange={setFreshSoph} />
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
              Sort by
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800 shadow-sm focus:border-slate-500 focus:outline-none"
              >
                <option value="verified_desc">Last verified (newest)</option>
                <option value="company_az">Company A–Z</option>
                <option value="role_az">Role A–Z</option>
              </select>
            </label>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Showing <span className="font-semibold text-slate-700">{filtered.length}</span> of{" "}
          {data.length} postings
        </p>
        <button
          type="button"
          onClick={reset}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          Reset filters
        </button>
      </div>

      {filtered.length === 0 ? (
        <div className="mt-10 text-center">
          <p className="text-sm text-slate-600">
            No postings match the current filters.
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Try a different search term or use{" "}
            <span className="font-medium text-slate-500">Reset filters</span> above.
          </p>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((item) => (
            <InternshipCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
