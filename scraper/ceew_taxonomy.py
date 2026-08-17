"""
CEEW's research-area taxonomy, as published under the "Research" tab at
https://www.ceew.in/ (fetched 2026-07-14).

This is used as the controlled vocabulary for the "sectoral relevance"
dimension of the bill climate-impact score. Update this list if CEEW
reorganizes its research areas — the scorer prompt pulls directly from
CEEW_AREAS, so a change here propagates automatically.
"""

CEEW_AREAS = {
    "Transformations": [
        "Low-Carbon Economy",
        "Energy Transitions",
        "Power Markets",
        "Industrial Sustainability",
        "Sustainable Livelihoods",
    ],
    "Quality of Life": [
        "Clean Air",
        "Sustainable Water",
        "Sustainable Food Systems",
        "Sustainable Cooling",
        "Sustainable Mobility",
    ],
    "Enablers": [
        "Sustainable Finance",
        "Technology Futures",
        "Circular Economy",
        "Climate Resilience",
        "International Cooperation",
    ],
}

# Flat list, useful for prompt construction and for validating scorer output
ALL_AREAS = [area for cluster in CEEW_AREAS.values() for area in cluster]


def area_cluster(area_name: str) -> str | None:
    """Return which of the 3 top-level clusters a given area belongs to."""
    for cluster, areas in CEEW_AREAS.items():
        if area_name in areas:
            return cluster
    return None
