"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { getAllQA } from "../../lib/data";

const HOUSE_STYLES: Record<string, string> = {
  "Lok Sabha": "text-blue",
  "Rajya Sabha": "text-green",
};

export default function QAPage() {
  const allEntries = getAllQA();
  const [house, setHouse] = useState("All houses");
  const [area, setArea] = useState("All areas");

  const areas = useMemo(
    () => Array.from(new Set(allEntries.map((e) => e.ceew_area).filter(Boolean))) as string[],
    [allEntries]
  );

  const filtered = useMemo(() => {
    return allEntries
      .filter((e) => e.is_relevant)
      .filter((e) => (house === "All houses" ? true : e.house === house))
      .filter((e) => (area === "All areas" ? true : e.ceew_area === area))
      .sort((a, b) => (b.answer_date ?? "").localeCompare(a.answer_date ?? ""));
  }, [allEntries, house, area]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <p className="max-w-2xl text-inkmuted mb-8 leading-relaxed">
        Questions MPs have asked ministers in Lok Sabha and Rajya Sabha on climate, energy, and
        sustainability topics, with the government&rsquo;s answers summarized and tagged against
        CEEW&rsquo;s research areas.
      </p>

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
              {entry.is_manual_override && (
                <span className="text-ink border border-ink px-1.5 rounded-sm">reviewed</span>
              )}
            </div>
            <div className="font-display text-lg text-ink leading-snug">{entry.title}</div>
            <div className="text-xs text-inkmuted mt-0.5">
              {entry.ministry ?? "Ministry unknown"}
              {entry.member_name ? ` \u00b7 asked by ${entry.member_name}` : ""}
              {entry.answer_date ? ` \u00b7 ${entry.answer_date}` : ""}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
