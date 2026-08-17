"""
Seed keywords used to (a) pull Google Trends interest-over-time via
SerpApi, and (b) search Reddit/YouTube for climate-relevant discussion.

These are *seeds* for search, not authoritative tags — the actual CEEW
area tagging for each item is decided by Claude in trend_scorer.py, which
reads the item's real title/content. A keyword landing here under one
area doesn't mean every result for it gets that area; it's just where we
go looking.
"""

CEEW_AREA_KEYWORDS: dict[str, list[str]] = {
    "Low-Carbon Economy": ["carbon tax India", "net zero India", "carbon credits India"],
    "Energy Transitions": ["renewable energy India", "solar power India", "coal phase out India"],
    "Power Markets": ["electricity tariff India", "power grid India", "discom India"],
    "Industrial Sustainability": ["green steel India", "industrial emissions India"],
    "Sustainable Livelihoods": ["green jobs India", "just transition India", "coal workers India"],
    "Clean Air": ["air pollution India", "AQI Delhi", "stubble burning"],
    "Sustainable Water": ["water crisis India", "groundwater India", "Jal Jeevan Mission"],
    "Sustainable Food Systems": ["food security India", "climate agriculture India"],
    "Sustainable Cooling": ["heatwave India", "cooling action plan India", "air conditioner India"],
    "Sustainable Mobility": ["electric vehicle India", "EV subsidy India", "public transport India"],
    "Sustainable Finance": ["green bonds India", "climate finance India"],
    "Technology Futures": ["critical minerals India", "battery storage India", "hydrogen India"],
    "Circular Economy": ["waste management India", "e-waste India", "recycling India"],
    "Climate Resilience": ["climate change India", "monsoon India", "flood India"],
    "International Cooperation": ["COP India", "climate finance negotiations India"],
}

ALL_SEED_KEYWORDS = sorted({kw for kws in CEEW_AREA_KEYWORDS.values() for kw in kws})

# Subreddits worth searching for India-focused climate/energy discussion
SUBREDDITS = ["india", "IndiaSpeaks", "indiadiscussion", "developedindia", "energy"]
