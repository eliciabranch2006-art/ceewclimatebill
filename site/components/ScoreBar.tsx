import type { Bill } from "../lib/data";

const SEGMENTS: { key: keyof Bill; label: string; max: number; color: string }[] = [
  { key: "sectoral_score", label: "Sectoral relevance", max: 30, color: "#000000" },
  { key: "mitigation_score", label: "Mitigation/adaptation substance", max: 25, color: "#86BB3F" },
  { key: "enforceability_score", label: "Enforceability", max: 20, color: "#009ED8" },
  { key: "scale_score", label: "Scale of impact", max: 15, color: "#F16223" },
  { key: "novelty_score", label: "Novelty", max: 10, color: "#B3B3B3" },
];

const TOTAL_MAX = SEGMENTS.reduce((sum, s) => sum + s.max, 0); // 100

/**
 * Renders the 5-part rubric as one horizontal bar, each segment sized to
 * its share of the 100-point total and filled proportionally to the
 * bill's actual score in that dimension. This is the one visual device
 * that shows up everywhere a score does (list rows and detail pages) —
 * it's meant to make the rubric legible at a glance, not just the total.
 */
export function ScoreBar({ bill, compact = false }: { bill: Bill; compact?: boolean }) {
  if (bill.total_score === null) {
    return (
      <div className="font-mono text-xs text-inkmuted italic">not yet scored</div>
    );
  }

  return (
    <div className="w-full">
      <div className={`flex w-full rounded-sm overflow-hidden ${compact ? "h-2" : "h-3"} bg-rule`}>
        {SEGMENTS.map((seg) => {
          const widthPct = (seg.max / TOTAL_MAX) * 100;
          const value = (bill[seg.key] as number | null) ?? 0;
          const fillPct = Math.max(0, Math.min(100, (value / seg.max) * 100));
          return (
            <div
              key={seg.key}
              style={{ width: `${widthPct}%` }}
              className="h-full relative bg-rule"
              title={`${seg.label}: ${value}/${seg.max}`}
            >
              <div
                className="h-full"
                style={{ width: `${fillPct}%`, backgroundColor: seg.color }}
              />
            </div>
          );
        })}
      </div>
      {!compact && (
        <div className="mt-1 flex justify-between text-[11px] font-mono text-inkmuted">
          <span>0</span>
          <span className="font-medium text-ink">{bill.total_score} / 100</span>
          <span>100</span>
        </div>
      )}
    </div>
  );
}
