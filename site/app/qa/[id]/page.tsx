import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllQA, getQAById } from "../../../lib/data";
import { AnswerCountdown } from "../../../components/AnswerCountdown";

export function generateStaticParams() {
  return getAllQA().map((e) => ({ id: e.id }));
}

export default function QADetailPage({ params }: { params: { id: string } }) {
  const entry = getQAById(decodeURIComponent(params.id));
  if (!entry) notFound();

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <Link href="/qa" className="text-xs font-mono text-inkmuted hover:text-ink">
        &larr; all Q&amp;A
      </Link>

      <div className="mt-4 flex items-center gap-2 flex-wrap text-xs font-mono">
        <span className="text-blue">{entry.house}</span>
        {entry.question_type && <span className="text-inkmuted">{entry.question_type}</span>}
        {entry.question_number && <span className="text-inkmuted">Q{entry.question_number}</span>}
        {entry.is_manual_override && (
          <span className="text-ink border border-ink px-1.5 rounded-sm">
            reviewed by outreach team
          </span>
        )}
      </div>

      <h1 className="font-display text-3xl font-semibold text-ink mt-3 leading-tight">
        {entry.title}
      </h1>
      <p className="text-sm text-inkmuted mt-2 font-mono">
        {entry.ministry ?? "Ministry unknown"}
        {entry.member_name ? ` \u00b7 asked by ${entry.member_name}` : ""}
      </p>
      {entry.member_constituency && (
        <p className="text-sm text-inkmuted font-mono">
          Representing: {entry.member_constituency}
        </p>
      )}

      {entry.ceew_area && (
        <span className="inline-block mt-4 text-xs font-mono px-2 py-0.5 bg-ink text-card rounded-sm">
          {entry.ceew_area}
        </span>
      )}

      {!entry.is_answered && (
        <div className="mt-5">
          <AnswerCountdown listedDate={entry.listed_date} />
        </div>
      )}

      {entry.summary_bullets.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display text-lg text-ink mb-2">Summary</h2>
          <ul className="space-y-1.5">
            {entry.summary_bullets.map((point, i) => (
              <li key={i} className="flex gap-2 text-sm text-inkmuted leading-relaxed">
                <span className="text-blue shrink-0">&bull;</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {entry.is_answered && entry.answer_text && (
        <section className="mt-6">
          <h2 className="font-display text-lg text-ink mb-2">Government&rsquo;s response</h2>
          <p className="text-sm text-inkmuted leading-relaxed whitespace-pre-line">
            {entry.answer_text}
          </p>
        </section>
      )}

      {entry.rationale && (
        <p className="mt-6 pt-4 border-t border-rule text-sm text-inkmuted leading-relaxed">
          {entry.rationale}
        </p>
      )}

      <p className="mt-4 text-[11px] font-mono text-inkmuted">
        confidence: {entry.confidence ?? "unknown"}
        {entry.scorer_model ? ` \u00b7 scored by ${entry.scorer_model}` : ""}
      </p>

      {entry.url && (
        <div className="mt-10 pt-6 border-t border-rule">
          <a
            href={entry.url}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-mono underline text-inkmuted hover:text-ink"
          >
            View on sansad.in &rarr;
          </a>
        </div>
      )}
    </div>
  );
}
