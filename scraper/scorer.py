"""
Climate-impact scoring for bills, using the rubric CEEW's outreach team
and Claude worked out together:

  Sectoral relevance   (0-30)  match to CEEW's 15 research areas
                                 - primary area: 20 pts
                                 - secondary areas: up to 10 pts total (~3-4 each)
  Mitigation/adaptation substance (0-25)  binding standards/targets/funding
                                            vs. rhetorical mention
  Enforceability       (0-20)  penalties, implementing authority vs. non-binding language
  Scale of impact       (0-15)  national vs. state, sector-wide vs. narrow
  Novelty               (0-10)  new law vs. minor amendment

Why an LLM and not keyword rules: classifying "does this bill set a
binding emissions standard" or "is this a narrow vs. sector-wide change"
is a reading-comprehension task, not a keyword-matching one. A rules-based
scorer would either be too coarse to trust or would require constant
hand-tuning. The trade-off is that every score needs a visible rationale
(so a reviewer can sanity-check it) and a confidence flag (so
low-confidence or borderline scores get surfaced for human review rather
than published silently) — both are built into the schema below.

Requires an ANTHROPIC_API_KEY (set as a GitHub Actions secret in
production). If it's not set, scoring is skipped and bills are stored
unscored — the site will show them as "not yet scored" rather than
guessing with a weaker heuristic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import anthropic

from ceew_taxonomy import ALL_AREAS

logger = logging.getLogger(__name__)

# Use haiku for cost efficiency on a high-volume classification task;
# swap to "claude-sonnet-5" via SCORER_MODEL env var if you want higher-
# quality rationale text and can absorb the extra cost (bill volume is
# low — a few hundred/year — so sonnet is affordable too).
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Bump this whenever SYSTEM_PROMPT's rubric/rules change in a way that could
# change existing scores (e.g. adding the minerals/reskilling classification
# rules). db.bill_needs_scoring() compares this to each bill's stored
# prompt_version and automatically re-scores anything scored under an older
# version — so a rubric fix propagates to already-scraped bills, not just
# newly-scraped ones.
PROMPT_VERSION = 2

SYSTEM_PROMPT = f"""You are scoring Indian parliamentary bills for their climate-policy \
relevance, for CEEW (Council on Energy, Environment and Water)'s outreach team. \
You will be given a bill's title, ministry, status, and PRS Legislative Research's own \
"Highlights" and "Key Issues and Analysis" summaries. Score the bill against this rubric \
and respond with ONLY a JSON object, no other text:

{{
  "sectoral_primary_area": "<one of CEEW's 15 areas listed below, or null if the bill has \
no climate/sustainability relevance at all>",
  "sectoral_secondary_areas": ["<0-3 additional areas from the list, or empty>"],
  "sectoral_score": <int 0-30>,
  "mitigation_score": <int 0-25>,
  "enforceability_score": <int 0-20>,
  "scale_score": <int 0-15>,
  "novelty_score": <int 0-10>,
  "total_score": <int, sum of the five scores above>,
  "rationale": "<2-4 sentences explaining the scores, plain language, for a non-technical outreach reader>",
  "confidence": "<high|medium|low>",
  "needs_review": <true if confidence is low OR if the bill is borderline/ambiguous \
in its climate relevance>,
  "highlights_bullets": ["<3-6 short bullet points capturing the substance of the \
'Highlights of the Bill' text — each bullet a single concrete provision, one sentence, \
no filler words>"],
  "issues_bullets": ["<2-5 short bullet points capturing the substance of the \
'Key Issues and Analysis' text — each bullet one concrete concern or open question, \
one sentence each>"]
}}

CEEW's 15 research areas (use exact names): {", ".join(ALL_AREAS)}

Scoring guidance:
- sectoral_score: 20 points if there's a clear primary-area match; up to 10 more points \
across secondary areas (roughly 3-4 pts each, capped at 10 total). 0 if no real match \
(e.g. a bill about court procedure or an unrelated constitutional amendment).
- mitigation_score: higher for bills that set binding emissions/environmental standards, \
funding mechanisms, or targets; lower for bills that merely mention climate/environment \
in passing or reference it rhetorically without substantive provisions.
- enforceability_score: higher for bills with penalties, a named implementing authority, \
or compliance mechanisms; lower for bills that are aspirational or non-binding.
- scale_score: higher for national-level, sector-wide bills; lower for narrow, \
localized, or single-institution bills.
- novelty_score: higher for genuinely new legislative frameworks; lower for minor/technical \
amendments to existing acts.
- Most bills in this dataset are NOT climate bills (PRS covers all of Parliament's business). \
Score honestly — a bill about, say, court fee amendments should score at or near 0 across \
the board, with sectoral_primary_area: null.

Classification rules from CEEW's outreach team (apply these before falling back to your \
own judgement):
- A bill whose main effect is on individual reskilling, upskilling, vocational training, or \
workforce transition — especially into green/clean-energy careers — should be classified \
under "Sustainable Livelihoods", even if it doesn't mention climate or energy directly.
- A bill whose main effect is on mineral extraction, critical minerals, mining, or mineral \
processing/refining should be classified under "Technology Futures", even though it may \
seem to fit "Low-Carbon Economy" or "Circular Economy" — CEEW's outreach team wants minerals \
bills grouped with Technology Futures specifically.

highlights_bullets / issues_bullets guidance: be genuinely succinct — a reader should be \
able to scan all bullets in under 10 seconds. Cut qualifiers, drop citations to section \
numbers unless essential, and prefer one clear sentence over two connected ones. If the \
source text is too thin to produce a real bullet (e.g. "(not available)"), return an empty list.
"""


def _build_user_prompt(bill: dict) -> str:
    return f"""Title: {bill['title']}
Ministry: {bill.get('ministry') or 'unknown'}
Status: {bill.get('status') or 'unknown'}
PRS category: {bill.get('prs_category') or 'unknown'}

Highlights of the Bill:
{bill.get('highlights_text') or '(not available)'}

Key Issues and Analysis:
{bill.get('key_issues_text') or '(not available)'}
"""


def score_bill(bill: dict, model: Optional[str] = None) -> Optional[dict]:
    """Score a single bill dict (as produced by prs_client.BillDetail.__dict__).
    Returns a dict matching the schema above, or None if no API key is set."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping scoring for %s", bill.get("id"))
        return None

    model = model or os.environ.get("SCORER_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(bill)}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Could not parse scorer output for %s: %r", bill.get("id"), raw_text)
        return None

    # Validate area names against the controlled vocabulary; don't let a
    # hallucinated area name silently corrupt the taxonomy filter on the site
    if parsed.get("sectoral_primary_area") not in ALL_AREAS + [None]:
        logger.warning("Unrecognized primary area %r for %s — clearing it",
                        parsed.get("sectoral_primary_area"), bill.get("id"))
        parsed["sectoral_primary_area"] = None
    parsed["sectoral_secondary_areas"] = [
        a for a in parsed.get("sectoral_secondary_areas", []) if a in ALL_AREAS
    ]
    parsed["sectoral_secondary_areas_json"] = json.dumps(parsed["sectoral_secondary_areas"])

    # Bullet fields are optional/best-effort — fall back to empty lists rather
    # than failing the whole score if the model omits them
    highlights_bullets = [str(b) for b in parsed.get("highlights_bullets", []) if b]
    issues_bullets = [str(b) for b in parsed.get("issues_bullets", []) if b]
    parsed["highlights_bullets_json"] = json.dumps(highlights_bullets)
    parsed["issues_bullets_json"] = json.dumps(issues_bullets)

    parsed["scorer_model"] = model
    return parsed
