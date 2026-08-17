const DIRECTION_STYLES: Record<string, string> = {
  supportive: "bg-green/10 text-green border border-green/40",
  harmful: "bg-orange/10 text-orange border border-orange/40",
  mixed: "bg-blue/10 text-blue border border-blue/40",
};

const DIRECTION_LABELS: Record<string, string> = {
  supportive: "climate-supportive",
  harmful: "climate-harmful",
  mixed: "mixed impact",
};

/** "neutral" and null are intentionally not rendered — they're the "no
 * strong signal" cases and would just add visual noise to the majority of
 * mildly-relevant administrative bills. */
export function ClimateDirectionBadge({ direction }: { direction: string | null }) {
  if (!direction || !(direction in DIRECTION_STYLES)) return null;
  return (
    <span className={`inline-block px-2 py-0.5 rounded-sm text-xs font-mono ${DIRECTION_STYLES[direction]}`}>
      {DIRECTION_LABELS[direction]}
    </span>
  );
}
