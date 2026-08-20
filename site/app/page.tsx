"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { getAllBills } from "../lib/data";
import { ScoreBar } from "../components/ScoreBar";
import { StatusPill } from "../components/StatusPill";
import { ClimateDirectionBadge } from "../components/ClimateDirectionBadge";

const CEEW_CLUSTERS: Record<string, string[]> = {
  Transformations: [
    "Low-Carbon Economy",
    "Energy Transitions",
    "Power Markets",
    "Industrial Sustainability",
    "Sustainable Livelihoods",
  ],
  "Quality of Life": [
    "Clean Air",
    "Sustainable Water",
    "Sustainable Food Systems",
    "Sustainable Cooling",
    "Sustainable Mobility",
  ],
  Enablers: [
    "Sustainable Finance",
    "Technology Futures",
    "Circular Economy",
    "Climate Resilience",
    "International Cooperation",
  ],
};

const STATUS_OPTIONS = ["All", "Passed", "Pending", "In Committee", "Draft", "Withdrawn", "Lapsed"];

const CUTOFF_YEARS = 2; // mirrors scraper/update_bills.py's CUTOFF_YEARS — frontend
                          // safety net in case older data ever slips through the export

type SortMode = "chronological" | "effective" | "non_climate" | "needs_review";

/** Latest known date for a bill — prefers its most recent status-timeline
 * entry (e.g. last action taken), falling back to its year. Used for the
 * chronological sort so bills with recent activity surface first, not just
 * bills that happen to have been introduced most recently. */
function latestActivityTime(bill: ReturnType<typeof getAllBills>[number]): number {
  const dates = bill.status_timeline
    .map((e) => (e.date ? Date.parse(e.date) : NaN))
    .filter((t) => !Number.isNaN(t));
  if (dates.length > 0) return Math.max(...dates);
  return bill.year ? Date.parse(`${bill.year}-01-01`) : 0;
}

export default function HomePage() {
  const allBills = getAllBills();
  const [query, setQuery] = useState("");
  const [area, setArea] = useState("All areas");
  const [status, setStatus] = useState("All");
  const [onlyScored, setOnlyScored] = useState(true);
  const [sortMode, setSortMode] = useState<SortMode>("chronological");

  const filtered = useMemo(() => {
    const cutoffYear = new Date().getFullYear() - CUTOFF_YEARS;
    const isNonClimateTab = sortMode === "non_climate";
    const isReviewTab = sortMode === "needs_review";

    const base = allBills
      .filter((b) => b.year === null || b.year >= cutoffYear)
      .filter((b) => (onlyScored ? b.total_score !== null : true))
      .filter((b) =>
        query.trim() === ""
          ? true
          : b.title.toLowerCase().includes(query.toLowerCase()) ||
            (b.ministry ?? "").toLowerCase().includes(query.toLowerCase())
      )
      .filter((b) => (status === "All" ? true : b.status === status))
      // A bill with no CEEW area match at all is "completely irrelevant" and
      // belongs on the Non-climate tab, not the main lists. Bills tagged via
      // the minerals -> Technology Futures / reskilling -> Sustainable
      // Livelihoods rules always have a primary area, so they're unaffected
      // and stay in the main lists as intended.
      .filter((b) => {
        if (isReviewTab) return b.needs_review; // cuts across relevant + irrelevant alike
        return isNonClimateTab ? b.sectoral_primary_area === null : b.sectoral_primary_area !== null;
      })
      .filter((b) =>
        isNonClimateTab || area === "All areas"
          ? true
          : b.sectoral_primary_area === area || b.sectoral_secondary_areas.includes(area)
      );

    if (sortMode === "effective") {
      return base.sort((a, b) => (b.total_score ?? -1) - (a.total_score ?? -1));
    }
    return base.sort((a, b) => latestActivityTime(b) - latestActivityTime(a));
  }, [allBills, query, area, status, onlyScored, sortMode]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <p className="max-w-2xl text-inkmuted mb-8 leading-relaxed">
        Every bill before Parliament, scored for climate-policy relevance against a rubric
        built around CEEW&rsquo;s own research areas &mdash; sectoral relevance, mitigation or
        adaptation substance, enforceability, scale, and novelty.
      </p>

      <div className="flex items-center gap-1 mb-5 border border-rule rounded-sm w-fit overflow-hidden">
        <button
          onClick={() => setSortMode("chronological")}
          className={`px-4 py-2 text-sm font-mono transition-colors ${
            sortMode === "chronological" ? "bg-blue text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          Newest first
        </button>
        <button
          onClick={() => setSortMode("effective")}
          className={`px-4 py-2 text-sm font-mono transition-colors ${
            sortMode === "effective" ? "bg-blue text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          Most effective
        </button>
        <button
          onClick={() => setSortMode("non_climate")}
          className={`px-4 py-2 text-sm font-mono transition-colors border-l border-rule ${
            sortMode === "non_climate" ? "bg-ink text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          Non-climate related
        </button>
        <button
          onClick={() => setSortMode("needs_review")}
          className={`px-4 py-2 text-sm font-mono transition-colors border-l border-rule ${
            sortMode === "needs_review" ? "bg-orange text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          Medium confidence
        </button>
      </div>

      {sortMode === "non_climate" && (
        <p className="text-xs text-inkmuted mb-5 font-mono">
          Bills the model found no real climate/sustainability relevance in. Bills about
          minerals or individual reskilling are tagged to a CEEW area by design and won&rsquo;t
          appear here &mdash; see the About page.
        </p>
      )}

      {sortMode === "needs_review" && (
        <p className="text-xs text-inkmuted mb-5 font-mono">
          Two kinds of bills land here: those marked <span className="text-orange">&#9873; auto-tagged</span> were
          pattern-matched by a title keyword rather than judged from the bill&rsquo;s full text (fast to verify
          &mdash; usually just confirming the obvious); those marked <span className="text-orange">&#9873; needs review</span> reflect
          genuine model uncertainty or borderline relevance. Correct any of these via
          scraper/overrides.json; once reviewed, a bill drops off this tab automatically.
        </p>
      )}

      <div className="flex flex-wrap gap-3 mb-8 items-center">
        <input
          type="text"
          placeholder="Search title or ministry&hellip;"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="px-3 py-2 bg-card border border-rule rounded-sm text-sm flex-1 min-w-[200px] focus:outline-none focus:ring-1 focus:ring-ink"
        />
        {sortMode !== "non_climate" && (
          <select
            value={area}
            onChange={(e) => setArea(e.target.value)}
            className="px-3 py-2 bg-card border border-rule rounded-sm text-sm"
          >
            <option>All areas</option>
            {Object.entries(CEEW_CLUSTERS).map(([cluster, areas]) => (
              <optgroup label={cluster} key={cluster}>
                {areas.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        )}
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="px-3 py-2 bg-card border border-rule rounded-sm text-sm"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-inkmuted font-mono">
          <input
            type="checkbox"
            checked={onlyScored}
            onChange={(e) => setOnlyScored(e.target.checked)}
          />
          scored only
        </label>
      </div>

      <div className="border border-rule rounded-sm bg-card overflow-hidden">
        {filtered.length === 0 && (
          <div className="p-8 text-center text-inkmuted text-sm">
            {sortMode === "non_climate"
              ? "No non-climate-related bills match these filters yet."
              : sortMode === "needs_review"
              ? "Nothing needs review right now."
              : "No bills match these filters yet."}
          </div>
        )}
        {filtered.map((bill, i) => (
          <Link
            key={bill.id}
            href={`/bills/${bill.id}`}
            className="block px-5 py-4 border-b border-rule last:border-b-0 hover:bg-paper transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <StatusPill status={bill.status} />
                  {bill.sectoral_primary_area && (
                    <span className="text-xs font-mono text-inkmuted">
                      {bill.sectoral_primary_area}
                    </span>
                  )}
                  <ClimateDirectionBadge direction={bill.climate_direction} />
                  {bill.needs_review && (
                    <span className="text-xs font-mono text-orange">
                      &#9873; {bill.auto_flagged ? "auto-tagged" : "needs review"}
                    </span>
                  )}
                </div>
                <div className="font-display text-lg text-ink leading-snug">{bill.title}</div>
                <div className="text-xs text-inkmuted mt-0.5">
                  {bill.ministry ?? "Ministry unknown"} &middot; {bill.year ?? "year unknown"}
                </div>
              </div>
              <div className="w-40 shrink-0 pt-1">
                <ScoreBar bill={bill} compact />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
