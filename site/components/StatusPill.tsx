const STATUS_STYLES: Record<string, string> = {
  Passed: "bg-ink text-card",
  Pending: "bg-amber/20 text-amber border border-amber/40",
  "In Committee": "bg-amber/20 text-amber border border-amber/40",
  Draft: "border border-inkmuted text-inkmuted",
  Withdrawn: "border border-inkmuted text-inkmuted line-through",
  Lapsed: "border border-inkmuted text-inkmuted line-through",
  Negatived: "border border-inkmuted text-inkmuted line-through",
};

export function StatusPill({ status }: { status: string | null }) {
  if (!status) return null;
  const style = STATUS_STYLES[status] ?? "border border-rule text-inkmuted";
  return (
    <span className={`inline-block px-2 py-0.5 rounded-sm text-xs font-mono ${style}`}>
      {status}
    </span>
  );
}
