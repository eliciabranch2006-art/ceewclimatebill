"use client";

import { useMemo, useState } from "react";
import { getTrendingItems } from "../../lib/data";

const SOURCE_LABELS: Record<string, string> = {
  google_trends: "Google Trends",
  reddit: "Reddit",
  youtube: "YouTube",
};

const SOURCE_COLORS: Record<string, string> = {
  google_trends: "text-blue",
  reddit: "text-orange",
  youtube: "text-green",
};

export default function TrendsPage() {
  const allItems = getTrendingItems();
  const [source, setSource] = useState("All sources");
  const [area, setArea] = useState("All areas");

  const areas = useMemo(
    () => Array.from(new Set(allItems.map((i) => i.ceew_area).filter(Boolean))) as string[],
    [allItems]
  );

  const filtered = useMemo(() => {
    return allItems
      .filter((i) => i.is_relevant)
      .filter((i) => (source === "All sources" ? true : i.source === source))
      .filter((i) => (area === "All areas" ? true : i.ceew_area === area))
      .sort((a, b) => (b.metric_value ?? 0) - (a.metric_value ?? 0));
  }, [allItems, source, area]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <p className="max-w-2xl text-inkmuted mb-8 leading-relaxed">
        Climate-relevant search queries, Reddit discussion, and YouTube content trending in
        India right now, tagged against CEEW&rsquo;s research areas. Refreshed daily.
      </p>

      <div className="flex flex-wrap gap-3 mb-8">
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          className="px-3 py-2 bg-card border border-rule rounded-sm text-sm"
        >
          <option>All sources</option>
          <option value="google_trends">Google Trends</option>
          <option value="reddit">Reddit</option>
          <option value="youtube">YouTube</option>
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
            No relevant trending items match these filters yet.
          </div>
        )}
        {filtered.map((item) => (
          <a
            key={item.id}
            href={item.url ?? undefined}
            target={item.url ? "_blank" : undefined}
            rel="noreferrer"
            className={`block px-5 py-4 border-b border-rule last:border-b-0 ${
              item.url ? "hover:bg-paper transition-colors cursor-pointer" : ""
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap text-xs font-mono">
                  <span className={SOURCE_COLORS[item.source]}>{SOURCE_LABELS[item.source]}</span>
                  {item.ceew_area && <span className="text-inkmuted">{item.ceew_area}</span>}
                </div>
                <div className="font-display text-lg text-ink leading-snug">{item.title}</div>
                {item.rationale && (
                  <div className="text-xs text-inkmuted mt-1">{item.rationale}</div>
                )}
              </div>
              {item.metric_value !== null && (
                <div className="text-right shrink-0">
                  <div className="font-mono text-lg text-ink">{item.metric_value}</div>
                  <div className="text-[11px] font-mono text-inkmuted">{item.metric_label}</div>
                </div>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
