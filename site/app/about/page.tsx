import Link from "next/link";

const RUBRIC = [
  {
    label: "Sectoral relevance",
    points: 30,
    color: "bg-black",
    body:
      "How closely the bill maps onto CEEW's own 15 research areas, grouped under Transformations, Quality of Life, and Enablers. A bill gets 20 points for a clear primary match to one area, plus up to 10 more points across secondary areas it also touches. A bill with no real climate or sustainability relevance scores 0 here.",
  },
  {
    label: "Mitigation / adaptation substance",
    points: 25,
    color: "bg-green",
    body:
      "Whether the bill actually does something — sets binding emissions or environmental standards, creates funding mechanisms, or establishes targets — versus merely mentioning climate or environment in passing.",
  },
  {
    label: "Enforceability",
    points: 20,
    color: "bg-blue",
    body:
      "Whether the bill has teeth: penalties for non-compliance, a named implementing authority, or a compliance mechanism — versus aspirational language with no enforcement path.",
  },
  {
    label: "Scale of impact",
    points: 15,
    color: "bg-orange",
    body:
      "Whether the bill applies nationally and sector-wide, or is narrow — limited to one state, one institution, or a small carve-out.",
  },
  {
    label: "Novelty",
    points: 10,
    color: "bg-[#B3B3B3]",
    body:
      "Whether the bill creates a genuinely new legislative framework, or is a minor/technical amendment to an existing act.",
  },
];

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <Link href="/" className="text-xs font-mono text-inkmuted hover:text-ink">
        &larr; all bills
      </Link>

      <h1 className="font-display text-3xl font-semibold text-ink mt-4 mb-3">
        How bills are scored
      </h1>
      <p className="text-inkmuted leading-relaxed">
        Every bill on this site is scored out of 100 for its climate-policy relevance, using a
        rubric CEEW&rsquo;s outreach team designed. The score is produced by an AI model (Claude),
        which reads each bill&rsquo;s official summary from{" "}
        <a
          href="https://prsindia.org/billtrack"
          target="_blank"
          rel="noreferrer"
          className="underline hover:text-ink"
        >
          PRS Legislative Research
        </a>{" "}
        and returns a score for each of the five dimensions below, along with a plain-language
        explanation of its reasoning.
      </p>

      <div className="mt-8 space-y-5">
        {RUBRIC.map((r) => (
          <div key={r.label} className="border border-rule rounded-sm p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-sm ${r.color}`} />
                <h2 className="font-display text-lg text-ink">{r.label}</h2>
              </div>
              <span className="font-mono text-sm text-inkmuted">{r.points} pts</span>
            </div>
            <p className="text-sm text-inkmuted leading-relaxed">{r.body}</p>
          </div>
        ))}
      </div>

      <h2 className="font-display text-xl text-ink mt-10 mb-3">Two classification rules</h2>
      <p className="text-inkmuted leading-relaxed mb-3">
        Two categories don&rsquo;t sort where you might expect, by outreach team design:
      </p>
      <ul className="space-y-2 mb-6">
        <li className="flex gap-2 text-sm text-inkmuted leading-relaxed">
          <span className="text-blue shrink-0">&bull;</span>
          <span>
            Bills mainly about individual reskilling, upskilling, or workforce transition —
            especially into green careers — are classified under{" "}
            <strong className="text-ink">Sustainable Livelihoods</strong>, even without an
            explicit climate or energy angle.
          </span>
        </li>
        <li className="flex gap-2 text-sm text-inkmuted leading-relaxed">
          <span className="text-blue shrink-0">&bull;</span>
          <span>
            Bills mainly about mineral extraction, critical minerals, mining, or processing are
            classified under <strong className="text-ink">Technology Futures</strong>, not
            Low-Carbon Economy or Circular Economy.
          </span>
        </li>
      </ul>

      <h2 className="font-display text-xl text-ink mt-10 mb-3">Confidence and review</h2>
      <p className="text-inkmuted leading-relaxed mb-3">
        Every score comes with a confidence level (high, medium, or low) from the model itself.
        Bills flagged &#9873;&nbsp;<strong className="text-ink">needs review</strong> are either
        low-confidence or genuinely borderline in their climate relevance — check the rationale on
        the bill&rsquo;s page before treating that score as final. CEEW&rsquo;s outreach team can
        hand-correct any score; bills marked{" "}
        <strong className="text-ink">reviewed by outreach team</strong> have had their score
        checked and adjusted by a person, and won&rsquo;t be silently overwritten by future
        automated scoring runs.
      </p>

      <h2 className="font-display text-xl text-ink mt-10 mb-3">What&rsquo;s shown here</h2>
      <p className="text-inkmuted leading-relaxed">
        This register only includes bills introduced within the last two years, refreshed daily
        from PRS Legislative Research. Bill text and status data are licensed by PRS under{" "}
        <a
          href="https://creativecommons.org/licenses/by/4.0/"
          target="_blank"
          rel="noreferrer"
          className="underline hover:text-ink"
        >
          CC BY 4.0
        </a>
        .
      </p>
    </div>
  );
}
