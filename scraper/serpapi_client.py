"""
Google Trends data via SerpApi (serpapi.com) — Google's own Trends API is
still gated/unavailable, and the unofficial pytrends library was blocked
by Google in 2025, so a paid intermediary is the reliable option. Free
tier is 100 searches/month; each keyword costs 1 search per run.

Two kinds of data:
  1. Real-time trending searches for India (what's hot right now, no
     keyword needed) — highest-signal for "what's on the public's mind."
  2. Interest-over-time for our curated CEEW keyword list — lets you see
     a keyword's trend line rather than just a single now/not-now signal.

Requires SERPAPI_KEY as an environment variable / GitHub secret.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


def _api_key() -> Optional[str]:
    return os.environ.get("SERPAPI_KEY")


def fetch_trending_now(geo: str = "IN") -> list[dict]:
    """Real-time trending search queries for India. Returns a list of
    {query, traffic_label} dicts. Returns [] if no API key is set."""
    key = _api_key()
    if not key:
        logger.warning("SERPAPI_KEY not set — skipping Google Trends 'trending now'")
        return []

    resp = requests.get(SERPAPI_BASE, params={
        "engine": "google_trends_trending_now",
        "geo": geo,
        "api_key": key,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("trending_searches", []):
        query = item.get("query")
        if not query:
            continue
        results.append({
            "query": query,
            "traffic_label": item.get("search_volume") or item.get("increase_percentage"),
        })
    return results


def fetch_interest_over_time(keyword: str, geo: str = "IN") -> Optional[dict]:
    """Interest-over-time for one keyword, last 90 days. Returns the most
    recent data point's value (0-100 relative interest scale) plus the
    trend direction vs. 30 days prior, or None on failure/no key."""
    key = _api_key()
    if not key:
        return None

    resp = requests.get(SERPAPI_BASE, params={
        "engine": "google_trends",
        "q": keyword,
        "geo": geo,
        "data_type": "TIMESERIES",
        "date": "today 3-m",
        "api_key": key,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    timeline = data.get("interest_over_time", {}).get("timeline_data", [])
    if not timeline:
        return None

    latest = timeline[-1]
    latest_value = latest.get("values", [{}])[0].get("extracted_value", 0)
    baseline_index = max(0, len(timeline) - 30)
    baseline_value = timeline[baseline_index].get("values", [{}])[0].get("extracted_value", 0)

    return {
        "keyword": keyword,
        "latest_value": latest_value,
        "baseline_value": baseline_value,
        "trend_pct": (
            round(((latest_value - baseline_value) / baseline_value) * 100, 1)
            if baseline_value else None
        ),
    }
