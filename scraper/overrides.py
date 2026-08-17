"""
Manual review overrides.

overrides.json is a plain, git-tracked file your team edits by hand
(in GitHub's web editor, or locally) to correct a score you disagree
with — no code or database access needed. Keyed by bill id (the slug
in the PRS URL, e.g. "the-forest-conservation-amendment-bill-2023").

Example entry:
{
  "the-forest-conservation-amendment-bill-2023": {
    "sectoral_primary_area": "Climate Resilience",
    "sectoral_secondary_areas": ["Sustainable Livelihoods"],
    "sectoral_score": 28,
    "mitigation_score": 10,
    "enforceability_score": 14,
    "scale_score": 15,
    "novelty_score": 6,
    "total_score": 73,
    "rationale": "Reviewed by outreach team 2026-07-20: model underweighted the exemption scale.",
    "confidence": "high",
    "needs_review": false,
    "reviewed_by": "<your name>"
  }
}

Any field you omit is left at the model's original value — you only
need to specify the fields you're correcting, except total_score, which
you should recompute by hand to keep it consistent.

Once a bill has an entry here, update_bills.py will never let the
automated scorer overwrite it (see db.upsert_score's is_manual_override
guard) until the entry is removed from this file.
"""

import json
from pathlib import Path

OVERRIDES_PATH = Path(__file__).resolve().parent / "overrides.json"


def load_overrides() -> dict:
    if not OVERRIDES_PATH.exists():
        return {}
    with open(OVERRIDES_PATH) as f:
        return json.load(f)


def apply_overrides(conn, now_iso: str):
    """Write every override into bill_scores with is_manual_override=1,
    so future automated scoring runs skip these bills."""
    overrides = load_overrides()
    for bill_id, fields in overrides.items():
        conn.execute(
            """INSERT INTO bill_scores (bill_id, sectoral_primary_area, sectoral_secondary_areas,
               sectoral_score, mitigation_score, enforceability_score, scale_score, novelty_score,
               total_score, rationale, confidence, needs_review, highlights_bullets, issues_bullets,
               scored_at, scorer_model, is_manual_override)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
               ON CONFLICT(bill_id) DO UPDATE SET
                 sectoral_primary_area=excluded.sectoral_primary_area,
                 sectoral_secondary_areas=excluded.sectoral_secondary_areas,
                 sectoral_score=excluded.sectoral_score,
                 mitigation_score=excluded.mitigation_score,
                 enforceability_score=excluded.enforceability_score,
                 scale_score=excluded.scale_score,
                 novelty_score=excluded.novelty_score,
                 total_score=excluded.total_score,
                 rationale=excluded.rationale,
                 confidence=excluded.confidence,
                 needs_review=excluded.needs_review,
                 highlights_bullets=excluded.highlights_bullets,
                 issues_bullets=excluded.issues_bullets,
                 scored_at=excluded.scored_at,
                 scorer_model=excluded.scorer_model,
                 is_manual_override=1""",
            (bill_id, fields.get("sectoral_primary_area"),
             json.dumps(fields.get("sectoral_secondary_areas", [])),
             fields.get("sectoral_score"), fields.get("mitigation_score"),
             fields.get("enforceability_score"), fields.get("scale_score"),
             fields.get("novelty_score"), fields.get("total_score"),
             fields.get("rationale"), fields.get("confidence", "high"),
             int(fields.get("needs_review", False)),
             json.dumps(fields.get("highlights_bullets", [])),
             json.dumps(fields.get("issues_bullets", [])),
             now_iso, f"manual:{fields.get('reviewed_by', 'unknown')}"),
        )
