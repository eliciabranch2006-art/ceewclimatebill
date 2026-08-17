"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { getAllQA } from "../../lib/data";

const HOUSE_STYLES: Record<string, string> = {
  "Lok Sabha": "text-blue",
  "Rajya Sabha": "text-green",
};

type ViewMode = "questions" | "regions" | "tally";

export default function QAPage() {
  const allEntries = getAllQA();
  const [view, setView] = useState<ViewMode>("questions");
  const [house, setHouse] = useState("All houses");
  const [area, setArea] = useState("All areas");

  const relevant = useMemo(() => allEntries.filter((e) => e.is_relevant), [allEntries]);

  const areas = useMemo(
    () => Array.from(new Set(relevant.map((e) => e.ceew_area).filter(Boolean))) as string[],
    [relevant]
  );

  const filtered = useMemo(() => {
    return relevant
      .filter((e) => (house === "All houses" ? true : e.house === house))
      .filter((e) => (area === "All areas" ? true : e.ceew_area === area))
      .sort((a, b) => (b.listed_date ?? "").localeCompare(a.listed_date ?? ""));
  }, [relevant, house, area]);

  // Region tally — grouped by the asking member's constituency/state
  const byRegion = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of filtered) {
      const region = e.member_constituency ?? "Unknown region";
      counts.set(region, (counts.get(region) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [filtered]);

  // CEEW-area tally — which areas are being asked about most
  const byArea = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of relevant) {
      if (!e.ceew_area) continue;
      counts.set(e.ceew_area, (counts.get(e.ceew_area) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [relevant]);
  const maxAreaCount = Math.max(1, ...byArea.map(([, c]) => c));

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <p className="max-w-2xl text-inkmuted mb-8 leading-relaxed">
        Questions MPs have asked ministers in Lok Sabha and Rajya Sabha on climate, energy, and
        sustainability topics, with the government&rsquo;s answers summarized and tagged against
        CEEW&rsquo;s research areas.
      </p>

      <div className="flex items-center gap-1 mb-5 border border-rule rounded-sm w-fit overflow-hidden">
        <button
          onClick={() => setView("questions")}
          className={`px-4 py-2 text-sm font-mono transition-colors ${
            view === "questions" ? "bg-blue text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          Questions
        </button>
        <button
          onClick={() => setView("regions")}
          className={`px-4 py-2 text-sm font-mono transition-colors border-l border-rule ${
            view === "regions" ? "bg-green text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          By region
        </button>
        <button
          onClick={() => setView("tally")}
          className={`px-4 py-2 text-sm font-mono transition-colors border-l border-rule ${
            view === "tally" ? "bg-orange text-white" : "text-inkmuted hover:bg-paper"
          }`}
        >
          By category
        </button>
      </div>

      {view !== "tally" && (
        <div className="flex flex-wrap gap-3 mb-8">
          <select
            value={house}
            onChange={(e) => setHouse(e.target.value)}
            className="px-3 py-2 bg-card border border-rule rounded-sm text-sm"
          >
            <option>All houses</option>
            <option>Lok Sabha</option>
            <option>Rajya Sabha</option>
          </select>
          <select
            value={area}
            onChange={(e) => setArea(e.target.value)}
            className="px-3 py-2 bg-card border border-rule rounded-sm text-sm"
          >
            <option>All areas</option>
            {areas.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </div>
      )}

      {view === "questions" && (
        <div className="border border-rule rounded-sm bg-card overflow-hidden">
          {filtered.length === 0 && (
            <div className="p-8 text-center text-inkmuted text-sm">
              No relevant Q&amp;A entries match these filters yet.
            </div>
          )}
          {filtered.map((entry) => (
            <Link
              key={entry.id}
              href={`/qa/${encodeURIComponent(entry.id)}`}
              className="block px-5 py-4 border-b border-rule last:border-b-0 hover:bg-paper transition-colors"
            >
              <div className="flex items-center gap-2 mb-1 flex-wrap text-xs font-mono">
                <span className={HOUSE_STYLES[entry.house]}>{entry.house}</span>
                {entry.question_type && <span className="text-inkmuted">{entry.question_type}</span>}
                {entry.ceew_area && <span className="text-inkmuted">{entry.ceew_area}</span>}
                {entry.member_constituency && (
                  <span className="text-inkmuted">{entry.member_constituency}</span>
                )}
                {!entry.is_answered && (
                  <span className="text-orange">awaiting answer</span>
                )}
                {entry.is_manual_override && (
                  <span className="text-ink border border-ink px-1.5 rounded-sm">reviewed</span>
                )}
              </div>
              <div className="font-display text-lg text-ink leading-snug">{entry.title}</div>
              <div className="text-xs text-inkmuted mt-0.5">
                {entry.ministry ?? "Ministry unknown"}
                {entry.member_name ? ` \u00b7 asked by ${entry.member_name}` : ""}
                {entry.listed_date ? ` \u00b7 ${entry.listed_date}` : ""}
              </div>
            </Link>
          ))}
        </div>
      )}

      {view === "regions" && (
        <div className="border border-rule rounded-sm bg-card overflow-hidden">
          {byRegion.length === 0 && (
            <div className="p-8 text-center text-inkmuted text-sm">No data yet.</div>
          )}
          {byRegion.map(([region, count]) => (
            <div
              key={region}
              className="flex items-center justify-between px-5 py-3 border-b border-rule last:border-b-0"
            >
              <span className="text-sm text-ink">{region}</span>
              <span className="font-mono text-sm text-inkmuted">{count}</span>
            </div>
          ))}
        </div>
      )}

      {view === "tally" && (
        <div className="border border-rule rounded-sm bg-card p-5">
          {byArea.length === 0 && (
            <div className="p-8 text-center text-inkmuted text-sm">No data yet.</div>
          )}
          <div className="space-y-3">
            {byArea.map(([a, count]) => (
              <div key={a} className="flex items-center gap-3">
                <span className="w-48 shrink-0 text-sm text-ink font-mono truncate">{a}</span>
                <div className="flex-1 h-3 bg-paper rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-blue"
                    style={{ width: `${(count / maxAreaCount) * 100}%` }}
                  />
                </div>
                <span className="w-8 text-right font-mono text-sm text-inkmuted">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
