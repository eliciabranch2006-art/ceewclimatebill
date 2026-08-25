const RUBRIC = [
  {
    label: "Sectoral relevance (0–30)",
    text: "How closely the bill maps onto CEEW's own 15 research areas, grouped under Transformations, Quality of Life, and Enablers. A bill gets 20 points for a clear primary match to one area, plus up to 10 more points across secondary areas it also touches. A bill with no real climate or sustainability relevance scores 0 here.",
  },
  {
    label: "Mitigation / adaptation substance (0–25)",
    text: "Whether the bill sets binding emissions or environmental standards, funding mechanisms, or targets — versus merely mentioning climate or environment in passing.",
  },
  {
    label: "Enforceability (0–20)",
    text: "Whether the bill includes penalties, a named implementing authority, or compliance mechanisms — versus being aspirational or non-binding.",
  },
  {
    label: "Scale of impact (0–15)",
    text: "Whether the bill is national and sector-wide, versus narrow or localized.",
  },
  {
    label: "Novelty (0–10)",
    text: "Whether the bill is a genuinely new legislative framework, versus a minor or technical amendment to an existing act.",
  },
];

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="font-display text-3xl font-semibold text-ink mb-4">About this site</h1>
      <p className="text-inkmuted leading-relaxed mb-8">
        This site tracks Indian parliamentary bills, public search/social trends, and
        parliamentary questions on climate, energy, and sustainability topics — built for
        CEEW&rsquo;s outreach team to see, at a glance, what&rsquo;s being discussed and
        legislated across the areas CEEW researches.
      </p>

      <h2 className="font-display text-xl text-ink mb-3">How bills are scored</h2>
      <p className="text-inkmuted leading-relaxed mb-4">
        Every bill is read by an AI model (Claude) and scored against a five-part rubric
        CEEW&rsquo;s outreach team designed, out of 100 points total:
      </p>
      <div className="space-y-4 mb-8">
        {RUBRIC.map((r) => (
          <div key={r.label} className="border-l-2 border-rule pl-4">
            <div className="font-mono text-sm text-ink mb-1">{r.label}</div>
            <div className="text-sm text-inkmuted leading-relaxed">{r.text}</div>
          </div>
        ))}
      </div>

      <h2 className="font-display text-xl text-ink mb-3">A "better safe than sorry" approach</h2>
      <p className="text-inkmuted leading-relaxed mb-4">
        The model is deliberately biased toward tagging a bill to a CEEW area rather than
        marking it irrelevant, when there's a plausible connection. A handful of categories
        are treated as hard rules rather than left to judgement: bills about cooperatives,
        livelihoods, or MSMEs always count under Sustainable Livelihoods; bills about minerals
        or mining always count under Technology Futures; bills about nuclear power or
        oilfields/petroleum always count under Energy Transitions; bills about disaster
        management count under Climate Resilience; water pollution bills count under
        Sustainable Water; boilers and industrial safety/emissions equipment count under
        Industrial Sustainability; and bills about mobility, shipping, ports, or vehicles of
        any kind count under Sustainable Mobility.
      </p>
      <p className="text-inkmuted leading-relaxed mb-4">
        Some bills are also flagged for their climate <em>direction</em> — not just whether
        they're relevant, but whether they help or work against climate goals. A bill
        expanding fossil fuel extraction, for instance, is tagged relevant to Energy
        Transitions <em>and</em> flagged as climate-harmful.
      </p>

      <h2 className="font-display text-xl text-ink mb-3">Confidence and review</h2>
      <p className="text-inkmuted leading-relaxed mb-4">
        Every score comes with a confidence level and a plain-language rationale. Bills
        worth a second look land on the "Medium confidence" tab — either because the model
        itself was genuinely unsure, or because a title-keyword rule had to step in and tag
        a bill the model missed (marked "auto-tagged"). CEEW's outreach team can correct any
        score by hand; once corrected, a bill is marked as reviewed and won't be
        automatically re-scored.
      </p>

      <h2 className="font-display text-xl text-ink mb-3">Data sources</h2>
      <p className="text-inkmuted leading-relaxed">
        Bill data comes from PRS Legislative Research, licensed CC BY 4.0. Trending-search
        data comes from Google Trends, Reddit, and YouTube. Parliamentary Q&amp;A data comes
        from sansad.in, the official portal for Lok Sabha and Rajya Sabha.
      </p>
    </div>
  );
}
