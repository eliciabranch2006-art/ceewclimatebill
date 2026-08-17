"""
Classifies a parliamentary Q&A entry for CEEW relevance/area and produces
a plain-language, succinct summary of what was asked and answered — the
same "succinct bullets, visible rationale, confidence flag" pattern used
for bills (scorer.py) and trending items (trend_scorer.py).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import anthropic

from ceew_taxonomy import ALL_AREAS

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = f"""You are screening a question asked in the Indian Parliament (Lok Sabha or \
Rajya Sabha) and the government's answer, for CEEW (Council on Energy, Environment and Water)'s \
outreach team — to track what MPs are asking ministers about on climate/energy/sustainability \
topics. Respond with ONLY a JSON object, no other text:

{{
  "is_relevant": <true if this genuinely concerns climate, energy, environment, or \
sustainability policy>,
  "ceew_area": "<one of CEEW's 15 areas below, or null if is_relevant is false>",
  "summary_bullets": ["<2-4 short bullets: what was asked and the substance of the answer, \
plain language, one sentence each>"],
  "rationale": "<one sentence on why this is or isn't relevant>",
  "confidence": "<high|medium|low>"
}}

CEEW's 15 research areas (use exact names): {", ".join(ALL_AREAS)}

Apply the same two classification rules used for CEEW's bill tracker: content about individual \
reskilling/green-careers goes under "Sustainable Livelihoods"; content about mineral extraction/ \
critical minerals goes under "Technology Futures".
"""


def _build_user_prompt(entry: dict) -> str:
    return f"""House: {entry.get('house')}
Ministry: {entry.get('ministry') or 'unknown'}
Question title: {entry.get('title')}

Question/answer text:
{(entry.get('question_text') or '(not available)')[:4000]}
"""


def classify_qa(entry: dict, model: Optional[str] = None) -> Optional[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping Q&A classification")
        return None

    model = model or os.environ.get("SCORER_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(entry)}],
    )
    raw_text = "".join(b.text for b in response.content if b.type == "text").strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Could not parse Q&A classifier output for %r: %r", entry.get("id"), raw_text)
        return None

    if parsed.get("ceew_area") not in ALL_AREAS + [None]:
        parsed["ceew_area"] = None
    parsed["summary_bullets_json"] = json.dumps(
        [str(b) for b in parsed.get("summary_bullets", []) if b]
    )
    parsed["scorer_model"] = model
    return parsed
