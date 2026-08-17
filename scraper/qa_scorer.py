"""
Classifies a parliamentary Q&A entry for CEEW relevance/area and produces
a plain-language, succinct summary of what was asked and (if available)
answered — the same "succinct bullets, visible rationale, confidence
flag" pattern used for bills (scorer.py) and trending items
(trend_scorer.py). Uses the same rubric/classification rules as the bills
scorer, and the same keyword safety net (keyword_rules.py), so a bill and
a parliamentary question about the same topic land in the same CEEW area.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import anthropic

from ceew_taxonomy import ALL_AREAS
from keyword_rules import match_forced_area

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# See scorer.PROMPT_VERSION for why this exists — bumped whenever the rules
# below change in a way that could change existing classifications.
PROMPT_VERSION = 1

SYSTEM_PROMPT = f"""You are screening a question asked in the Indian Parliament (Lok Sabha or \
Rajya Sabha) and the government's answer (if it has been given yet), for CEEW (Council on \
Energy, Environment and Water)'s outreach team — to track what MPs are asking ministers about \
on climate/energy/sustainability topics. Respond with ONLY a JSON object, no other text:

{{
  "is_relevant": <true if this genuinely concerns climate, energy, environment, or \
sustainability policy, or any of CEEW's 15 areas below — err toward inclusion, "better safe \
than sorry", the same way as CEEW's bill tracker>,
  "ceew_area": "<one of CEEW's 15 areas below, or null if is_relevant is false>",
  "summary_bullets": ["<2-4 short bullets: what was asked, and — only if an answer is \
provided in the text below — the substance of the government's response. If no answer text \
is provided, summarize only the question and do not invent or guess at a response.>"],
  "rationale": "<one sentence on why this is or isn't relevant>",
  "confidence": "<high|medium|low>"
}}

CEEW's 15 research areas (use exact names): {", ".join(ALL_AREAS)}

Classification rules (same ones used for CEEW's bill tracker — apply before falling back to \
your own judgement):
- Livelihoods, cooperatives, MSMEs: questions about livelihoods, cooperatives, or Micro, \
Small and Medium Enterprises go under "Sustainable Livelihoods".
- Minerals: questions about mineral extraction, critical minerals, or mining go under \
"Technology Futures".
- Nuclear and oilfields/petroleum: go under "Energy Transitions".
- Disaster management: goes under "Climate Resilience".
- Water pollution: goes under "Sustainable Water".
- Boilers/industrial safety/emissions equipment: goes under "Industrial Sustainability".
- Mobility, ports, and vehicles: any question about mobility, shipping, ports, railways, \
aviation, or vehicles of any kind goes under "Sustainable Mobility".
"""


def _build_user_prompt(entry: dict) -> str:
    answer_section = (
        entry.get("answer_text") or "(No answer text available — likely not yet answered. "
        "Do not guess at what the response might say.)"
    )
    return f"""House: {entry.get('house')}
Ministry: {entry.get('ministry') or 'unknown'}
Question title: {entry.get('title')}

Question text:
{(entry.get('question_text') or '(not available)')[:3000]}

Answer text:
{answer_section[:3000]}
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

    # Same keyword safety net as bills — only fills in when the model found nothing
    if parsed.get("ceew_area") is None:
        forced_area = match_forced_area(entry.get("title", ""))
        if forced_area is not None:
            parsed["ceew_area"] = forced_area
            parsed["is_relevant"] = True
            parsed["confidence"] = "low"
            note = f"Auto-flagged under {forced_area} based on the question's title; please verify."
            parsed["rationale"] = f"{parsed.get('rationale', '').strip()} ({note})".strip()

    parsed["summary_bullets_json"] = json.dumps(
        [str(b) for b in parsed.get("summary_bullets", []) if b]
    )
    parsed["scorer_model"] = model
    return parsed
