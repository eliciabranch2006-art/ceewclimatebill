import fs from "fs";
import path from "path";

/**
 * Loads JSON at BUILD TIME as plain data (JSON.parse returns `any`),
 * instead of a static `import x from "./y.json"`, which forces
 * TypeScript to infer the exact literal type of the entire file's
 * contents. That's fine for a small seed file, but once real scraped
 * data grows to hundreds of entries with long text fields, that
 * inference step can become extremely memory-hungry and has been known
 * to silently kill Vercel's build during the "checking validity of
 * types" phase — no reported error, just a dead build. Reading the file
 * and casting explicitly sidesteps that inference entirely; we get the
 * exact same runtime data either way.
 */
function readJson<T>(relativePath: string): T {
  const filePath = path.join(process.cwd(), relativePath);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

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

const bills = readJson<BillsFile>("data/bills.json");

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

const trends = readJson<TrendsFile>("data/trends.json");

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

const qa = readJson<QAFile>("data/qa.json");

export function getAllQA(): QAEntry[] {
  return qa.entries;
}

export function getQAById(id: string): QAEntry | undefined {
  return qa.entries.find((e) => e.id === id);
}

export function getQAGeneratedAt(): string {
  return qa.generated_at;
}
