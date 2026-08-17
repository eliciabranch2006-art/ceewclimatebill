"""
YouTube search via the YouTube Data API v3. Requires a free API key from
Google Cloud Console (console.cloud.google.com -> APIs & Services ->
Credentials -> Create API Key, with "YouTube Data API v3" enabled on the
project). Free quota is 10,000 units/day; a search.list call costs 100
units, so ~100 searches/day before hitting the quota — plenty for a daily
run over ~15 keywords.

Requires YOUTUBE_API_KEY as an environment variable / GitHub secret.
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_videos(query: str, region_code: str = "IN", max_results: int = 8) -> list[dict]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not set — skipping YouTube")
        return []

    resp = requests.get(SEARCH_URL, params={
        "part": "snippet",
        "q": query,
        "regionCode": region_code,
        "relevanceLanguage": "en",
        "type": "video",
        "order": "relevance",
        "maxResults": max_results,
        "key": api_key,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not video_id:
            continue
        results.append({
            "video_id": video_id,
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "description": (snippet.get("description") or "")[:500],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })
    return results
