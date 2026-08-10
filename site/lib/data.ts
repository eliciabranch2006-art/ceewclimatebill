import billsData from "../data/bills.json";

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
  scored_at: string | null;
  scorer_model: string | null;
  is_manual_override: boolean;
};

type BillsFile = {
  generated_at: string;
  source: string;
  bills: Bill[];
};

const data = billsData as BillsFile;

export function getAllBills(): Bill[] {
  return data.bills;
}

export function getScoredBills(): Bill[] {
  return data.bills.filter((b) => b.total_score !== null);
}

export function getBillById(id: string): Bill | undefined {
  return data.bills.find((b) => b.id === id);
}

export function getGeneratedAt(): string {
  return data.generated_at;
}

export function getDataSource(): string {
  return data.source;
}
