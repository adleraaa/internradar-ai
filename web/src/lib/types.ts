// TypeScript types mirroring data/schema.json (InternRadar AI).
// These fields and enum values match the root JSON schema exactly.
// Do not invent fields here that do not exist in data/schema.json.

export type Category =
  | "Software Engineering"
  | "AI/ML"
  | "Data Science"
  | "Product"
  | "Hardware"
  | "Other";

export type LocationType = "Remote" | "Hybrid" | "Onsite" | "Multiple" | "Unclear";

export type Status = "Open" | "Closed" | "Unclear";

export type SourceType =
  | "Company Career Page"
  | "Greenhouse"
  | "Lever"
  | "Ashby"
  | "Workday"
  | "Simplify"
  | "Handshake"
  | "LinkedIn"
  | "Other";

export type Relevance = "High" | "Medium" | "Low" | "None" | "Unclear";

export type StudentLevel =
  | "Freshman"
  | "Sophomore"
  | "Junior"
  | "Senior"
  | "Undergraduate"
  | "Graduate"
  | "Unclear";

export type YesNoUnclear = "Yes" | "No" | "Unclear";

export type CompensationCurrency = "USD" | "Other" | "Unclear";

export type CompensationPeriod =
  | "Hour"
  | "Month"
  | "Year"
  | "Stipend"
  | "Unpaid"
  | "Other"
  | "Unclear";

export interface Internship {
  id: string;
  company: string;
  role: string;
  category: Category;
  location: string;
  location_type: LocationType;
  internship_term: string;
  application_url: string;
  source_url: string;
  source_type: SourceType;
  status: Status;
  last_verified_date: string;
  discovered_date: string;
  age_days: number;
  tech_keywords: string[];
  ai_relevance: Relevance;
  full_stack_relevance: Relevance;
  student_level: StudentLevel;
  freshman_sophomore_friendly: YesNoUnclear;
  requires_us_citizenship: YesNoUnclear;
  sponsorship_note: string;
  work_authorization_note: string;
  evidence_notes: string;
  fit_summary: string;
  risk_flags: string[];
  compensation_min: number | null;
  compensation_max: number | null;
  compensation_currency: CompensationCurrency;
  compensation_period: CompensationPeriod;
  compensation_note: string;
  compensation_evidence: string;
  date_added: string;
  date_updated: string;
}
