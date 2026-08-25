"use client";

export function AnswerCountdown({ listedDate }: { listedDate: string | null }) {
  if (!listedDate) {
    return (
      <div className="text-xs font-mono text-inkmuted border border-rule rounded-sm px-3 py-2">
        No scheduled answer date found yet.
      </div>
    );
  }

  const target = Date.parse(listedDate);
  if (Number.isNaN(target)) {
    return (
      <div className="text-xs font-mono text-inkmuted border border-rule rounded-sm px-3 py-2">
        Scheduled for {listedDate}
      </div>
    );
  }

  const msRemaining = target - Date.now();
  const daysRemaining = Math.ceil(msRemaining / (1000 * 60 * 60 * 24));

  if (daysRemaining < 0) {
    return (
      <div className="text-xs font-mono text-orange border border-orange/40 bg-orange/10 rounded-sm px-3 py-2">
        Overdue — was scheduled for {listedDate}, no answer captured yet
      </div>
    );
  }

  if (daysRemaining === 0) {
    return (
      <div className="text-xs font-mono text-blue border border-blue/40 bg-blue/10 rounded-sm px-3 py-2">
        Due today ({listedDate})
      </div>
    );
  }

  return (
    <div className="text-xs font-mono text-inkmuted border border-rule rounded-sm px-3 py-2">
      <span className="text-ink text-sm font-medium">{daysRemaining}</span> day
      {daysRemaining === 1 ? "" : "s"} until scheduled answer ({listedDate})
    </div>
  );
}
