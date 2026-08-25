import billsData from "../data/bills.json";
import trendsData from "../data/trends.json";
import qaData from "../data/qa.json";

// See json-imports.d.ts — these imports are typed `any` by that ambient
// declaration (not inferred from the file contents), which is why the
// casts below are load-bearing rather than redundant: they're what give
// each dataset its real shape.

// ---------- Bills ----------

export type StatusTimelineEntry = {
  stage: string;
  chamber: string | null;
  date: string | null;
};

export type Bill = {
  id: string;
  title: string;
  prs_url: string;
  ministry: string | null;
  prs_category: string | null;
  status: string | null;
  year: number | null;
  overview_text: string | null;
  highlights_text: string | null;
  key_issues_text: string | null;
  status_timeline: StatusTimelineEntry[];
  bill_pdf_url: string | null;
  first_seen_at: string;
  last_scraped_at: string;
  sectoral_primary_area: string | null;
  sectoral_secondary_areas: string[];
  sectoral_score: number | null;
  mitigation_score: number | null;
  enforceability_score: number | null;
  scale_score: number | null;
  novelty_score: number | null;
  total_score: number | null;
  rationale: string | null;
  confidence: "high" | "medium" | "low" | null;
  needs_review: boolean;
  highlights_bullets: string[];
  issues_bullets: string[];
  scored_at: string | null;
  scorer_model: string | null;
  is_manual_override: boolean;
  climate_direction: "supportive" | "harmful" | "mixed" | "neutral" | null;
  climate_direction_rationale: string | null;
  auto_flagged: boolean;
};

type BillsFile = {
  generated_at: string;
  source: string;
  bills: Bill[];
};

const bills = billsData as BillsFile;

export function getAllBills(): Bill[] {
  return bills.bills;
}

export function getScoredBills(): Bill[] {
  return bills.bills.filter((b) => b.total_score !== null);
}

export function getBillById(id: string): Bill | undefined {
  return bills.bills.find((b) => b.id === id);
}

export function getGeneratedAt(): string {
  return bills.generated_at;
}

export function getDataSource(): string {
  return bills.source;
}

// ---------- Trends ----------

export type TrendingItem = {
  id: string;
  source: "google_trends" | "reddit" | "youtube";
  title: string;
  url: string | null;
  metric_label: string | null;
  metric_value: number | null;
  seed_keyword: string | null;
  is_relevant: boolean;
  ceew_area: string | null;
  rationale: string | null;
  confidence: "high" | "medium" | "low" | null;
  scorer_model: string | null;
  fetched_at: string;
};

type TrendsFile = {
  generated_at: string;
  items: TrendingItem[];
};

const trends = trendsData as TrendsFile;

export function getTrendingItems(): TrendingItem[] {
  return trends.items;
}

export function getTrendsGeneratedAt(): string {
  return trends.generated_at;
}

// ---------- Q&A ----------

export type QAEntry = {
  id: string;
  house: "Lok Sabha" | "Rajya Sabha";
  question_number: string | null;
  question_type: string | null;
  title: string;
  member_name: string | null;
  member_constituency: string | null;
  ministry: string | null;
  listed_date: string | null;
  question_text: string | null;
  answer_text: string | null;
  is_answered: boolean;
  url: string | null;
  is_relevant: boolean;
  ceew_area: string | null;
  summary_bullets: string[];
  rationale: string | null;
  confidence: "high" | "medium" | "low" | null;
  scorer_model: string | null;
  is_manual_override: boolean;
  first_seen_at: string;
  last_scraped_at: string;
};

type QAFile = {
  generated_at: string;
  source: string;
  entries: QAEntry[];
};

const qa = qaData as QAFile;

export function getAllQA(): QAEntry[] {
  return qa.entries;
}

export function getQAById(id: string): QAEntry | undefined {
  return qa.entries.find((e) => e.id === id);
}

export function getQAGeneratedAt(): string {
  return qa.generated_at;
}
