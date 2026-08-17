"use client";

/**
 * Shows time remaining until a question's scheduled listed_date, or an
 * "overdue" state past that date with no answer yet. This is NOT a
 * 15-day-from-asking countdown — that 15-day figure is the advance
 * notice an MP must give before a question is even listed, not a
 * government reply deadline. Once a question is listed, the written
 * answer is delivered on that specific scheduled date, so the honest
 * thing to show is a countdown to THAT date — see the About page for
 * the full explanation.
 */
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
