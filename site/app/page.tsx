"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { getAllBills } from "../lib/data";
import { ScoreBar } from "../components/ScoreBar";
import { StatusPill } from "../components/StatusPill";

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

export default function HomePage() {
  const allBills = getAllBills();
  const [query, setQuery] = useState("");
  const [area, setArea] = useState("All areas");
  const [status, setStatus] = useState("All");
  const [onlyScored, setOnlyScored] = useState(true);

  const filtered = useMemo(() => {
    return allBills
      .filter((b) => (onlyScored ? b.total_score !== null : true))
      .filter((b) =>
        query.trim() === ""
          ? true
          : b.title.toLowerCase().includes(query.toLowerCase()) ||
            (b.ministry ?? "").toLowerCase().includes(query.toLowerCase())
      )
      .filter((b) =>
        area === "All areas"
          ? true
          : b.sectoral_primary_area === area || b.sectoral_secondary_areas.includes(area)
      )
      .filter((b) => (status === "All" ? true : b.status === status))
      .sort((a, b) => (b.total_score ?? -1) - (a.total_score ?? -1));
  }, [allBills, query, area, status, onlyScored]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <p className="max-w-2xl text-inkmuted mb-8 leading-relaxed">
        Every bill before Parliament, scored for climate-policy relevance against a rubric
        built around CEEW&rsquo;s own research areas &mdash; sectoral relevance, mitigation or
        adaptation substance, enforceability, scale, and novelty.
      </p>

      <div className="flex flex-wrap gap-3 mb-8 items-center">
        <input
          type="text"
          placeholder="Search title or ministry&hellip;"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="px-3 py-2 bg-card border border-rule rounded-sm text-sm flex-1 min-w-[200px] focus:outline-none focus:ring-1 focus:ring-ink"
        />
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
            No bills match these filters yet.
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
                  {bill.needs_review && (
                    <span className="text-xs font-mono text-amber">&#9873; needs review</span>
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
