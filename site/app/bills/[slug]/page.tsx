import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllBills, getBillById } from "../../../lib/data";
import { ScoreBar } from "../../../components/ScoreBar";
import { StatusPill } from "../../../components/StatusPill";

export function generateStaticParams() {
  return getAllBills().map((b) => ({ slug: b.id }));
}

const RUBRIC_ROWS: { key: keyof NonNullable<ReturnType<typeof getBillById>>; label: string; max: number }[] = [
  { key: "sectoral_score", label: "Sectoral relevance", max: 30 },
  { key: "mitigation_score", label: "Mitigation / adaptation substance", max: 25 },
  { key: "enforceability_score", label: "Enforceability", max: 20 },
  { key: "scale_score", label: "Scale of impact", max: 15 },
  { key: "novelty_score", label: "Novelty", max: 10 },
];

export default function BillDetailPage({ params }: { params: { slug: string } }) {
  const bill = getBillById(params.slug);
  if (!bill) notFound();

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <Link href="/" className="text-xs font-mono text-inkmuted hover:text-ink">
        &larr; all bills
      </Link>

      <div className="mt-4 flex items-center gap-2 flex-wrap">
        <StatusPill status={bill.status} />
        {bill.is_manual_override && (
          <span className="text-xs font-mono text-ink border border-ink px-2 py-0.5 rounded-sm">
            reviewed by outreach team
          </span>
        )}
        {bill.needs_review && !bill.is_manual_override && (
          <span className="text-xs font-mono text-amber">&#9873; needs review</span>
        )}
      </div>

      <h1 className="font-display text-3xl font-semibold text-ink mt-3 leading-tight">
        {bill.title}
      </h1>
      <p className="text-sm text-inkmuted mt-2 font-mono">
        {bill.ministry ?? "Ministry unknown"} &middot; {bill.year ?? "year unknown"} &middot;{" "}
        {bill.prs_category ?? "category unknown"}
      </p>

      {bill.total_score !== null && (
        <section className="mt-8 border border-rule rounded-sm bg-card p-5">
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="font-display text-lg text-ink">Climate-impact score</h2>
            <span className="font-mono text-2xl text-ink">{bill.total_score}/100</span>
          </div>
          <ScoreBar bill={bill} />

          <div className="mt-5 space-y-2">
            {RUBRIC_ROWS.map((row) => (
              <div key={row.key} className="flex items-center justify-between text-sm">
                <span className="text-inkmuted">{row.label}</span>
                <span className="font-mono text-ink">
                  {bill[row.key] as number} / {row.max}
                </span>
              </div>
            ))}
          </div>

          {(bill.sectoral_primary_area || bill.sectoral_secondary_areas.length > 0) && (
            <div className="mt-4 pt-4 border-t border-rule flex flex-wrap gap-2">
              {bill.sectoral_primary_area && (
                <span className="text-xs font-mono px-2 py-0.5 bg-ink text-card rounded-sm">
                  {bill.sectoral_primary_area}
                </span>
              )}
              {bill.sectoral_secondary_areas.map((a) => (
                <span
                  key={a}
                  className="text-xs font-mono px-2 py-0.5 border border-rule text-inkmuted rounded-sm"
                >
                  {a}
                </span>
              ))}
            </div>
          )}

          {bill.rationale && (
            <p className="mt-4 pt-4 border-t border-rule text-sm text-inkmuted leading-relaxed">
              {bill.rationale}
            </p>
          )}

          <p className="mt-4 text-[11px] font-mono text-inkmuted">
            confidence: {bill.confidence ?? "unknown"} &middot; scored by {bill.scorer_model} on{" "}
            {bill.scored_at ? new Date(bill.scored_at).toLocaleDateString("en-IN") : "unknown date"}
          </p>
        </section>
      )}

      {bill.highlights_text && (
        <section className="mt-8">
          <h2 className="font-display text-lg text-ink mb-2">Highlights of the bill</h2>
          <p className="text-sm text-inkmuted leading-relaxed whitespace-pre-line">
            {bill.highlights_text}
          </p>
        </section>
      )}

      {bill.key_issues_text && (
        <section className="mt-6">
          <h2 className="font-display text-lg text-ink mb-2">Key issues and analysis</h2>
          <p className="text-sm text-inkmuted leading-relaxed whitespace-pre-line">
            {bill.key_issues_text}
          </p>
        </section>
      )}

      {bill.status_timeline.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display text-lg text-ink mb-3">Status timeline</h2>
          <ol className="space-y-2">
            {bill.status_timeline.map((entry, i) => (
              <li key={i} className="flex items-center gap-3 text-sm font-mono">
                <span className="w-2 h-2 rounded-full bg-ink shrink-0" />
                <span className="text-ink">{entry.stage}</span>
                <span className="text-inkmuted">{entry.chamber}</span>
                <span className="text-inkmuted ml-auto">{entry.date}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <div className="mt-10 pt-6 border-t border-rule flex gap-4 text-sm font-mono">
        <a href={bill.prs_url} target="_blank" rel="noreferrer" className="underline text-inkmuted hover:text-ink">
          View on PRS &rarr;
        </a>
        {bill.bill_pdf_url && (
          <a href={bill.bill_pdf_url} target="_blank" rel="noreferrer" className="underline text-inkmuted hover:text-ink">
            Bill PDF &rarr;
          </a>
        )}
      </div>
    </div>
  );
}
