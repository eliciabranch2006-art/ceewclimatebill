"""
Classifies a trending item (Google Trends query, Reddit post, or YouTube
video) for climate/CEEW relevance and tags it against CEEW's 15 areas.
Same design principle as scraper/scorer.py for bills: a short, visible
rationale and a confidence flag, rather than a silent black-box tag.
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

SYSTEM_PROMPT = f"""You are screening trending public content (a Google Trends search query, a \
Reddit post, or a YouTube video) for CEEW (Council on Energy, Environment and Water)'s outreach \
team, to spot what the Indian public is currently thinking about on climate/energy/sustainability \
topics. Respond with ONLY a JSON object, no other text:

{{
  "is_relevant": <true if this genuinely relates to climate, energy, environment, or \
sustainability in India — not just tangentially>,
  "ceew_area": "<one of CEEW's 15 areas below, or null if is_relevant is false>",
  "rationale": "<one sentence, plain language, on why this is or isn't relevant>",
  "confidence": "<high|medium|low>"
}}

CEEW's 15 research areas (use exact names): {", ".join(ALL_AREAS)}

Be conservative: a lot of trending content mentions "green," "climate," or "sustainable" in \
passing (marketing, unrelated news) without being substantively about these topics. Mark those \
is_relevant: false. Apply the same two classification rules used for CEEW's bill tracker: \
content about individual reskilling/green-careers goes under "Sustainable Livelihoods"; content \
about mineral extraction/critical minerals goes under "Technology Futures".
"""


def _build_user_prompt(item: dict) -> str:
    return f"""Source: {item['source']}
Title/query: {item['title']}
Extra context: {item.get('context') or '(none)'}
"""


def classify_item(item: dict, model: Optional[str] = None) -> Optional[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping classification")
        return None

    model = model or os.environ.get("SCORER_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(item)}],
    )
    raw_text = "".join(b.text for b in response.content if b.type == "text").strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Could not parse classifier output for %r: %r", item.get("title"), raw_text)
        return None

    if parsed.get("ceew_area") not in ALL_AREAS + [None]:
        parsed["ceew_area"] = None
    parsed["scorer_model"] = model
    return parsed
