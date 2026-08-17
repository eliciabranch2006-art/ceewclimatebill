"""
Shared deterministic keyword rules — a backstop for when the LLM doesn't
reliably apply the prompt's classification rules (this is exactly what
happened with MSME/cooperative bills: the prompt said to tag them, but a
probabilistic model won't apply every rule with 100% consistency). Used
by both scorer.py (bills) and qa_scorer.py (parliamentary Q&A) so the
same title triggers the same area everywhere on the site.
"""

FORCE_AREA_KEYWORDS: list[tuple[list[str], str]] = [
    (["cooperative", "co-operative", "livelihood",
      "micro, small and medium enterprises", "msme"], "Sustainable Livelihoods"),
    (["mineral", "mining"], "Technology Futures"),
    (["nuclear"], "Energy Transitions"),
    (["oilfield", "oil field", "petroleum"], "Energy Transitions"),
    (["disaster management"], "Climate Resilience"),
    (["water (prevention", "prevention and control of pollution"], "Sustainable Water"),
    (["boiler"], "Industrial Sustainability"),
    (["shipping", "carriage of goods by sea", "coastal shipping", "merchant shipping",
      "port ", "ports)", "railway", "motor vehicle", "aviation", "airport"], "Sustainable Mobility"),
]


def match_forced_area(text: str) -> str | None:
    """Returns the CEEW area a forced keyword match implies, or None."""
    text_lower = text.lower()
    for keywords, area in FORCE_AREA_KEYWORDS:
        if any(kw in text_lower for kw in keywords):
            return area
    return None
