"""
Entry point for the trends update job (run by
.github/workflows/update-trends.yml, or manually with
`python update_trends.py`).

Pulls: Google Trends (real-time trending + interest-over-time for the
CEEW keyword list), Reddit search results, and YouTube search results —
classifies each for CEEW relevance/area with Claude, stores in SQLite,
and exports site/data/trends.json.

Any source whose API key isn't set is silently skipped (not a hard
failure), so you can turn this on incrementally — e.g. get Google Trends
working before bothering with Reddit/YouTube.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import db
import reddit_client
import serpapi_client
import youtube_client
from trend_keywords import ALL_SEED_KEYWORDS, CEEW_AREA_KEYWORDS, SUBREDDITS
from trend_scorer import classify_item

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SITE_DATA_PATH = Path(__file__).resolve().parent.parent / "site" / "data" / "trends.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify_and_store(conn, source: str, item_id: str, title: str, url: str | None,
                         metric_label: str | None, metric_value: float | None,
                         seed_keyword: str | None, context: str | None = None):
    classification = classify_item({"source": source, "title": title, "context": context}) or {}
    db.upsert_trending_item(conn, {
        "id": item_id,
        "source": source,
        "title": title,
        "url": url,
        "metric_label": metric_label,
        "metric_value": metric_value,
        "seed_keyword": seed_keyword,
        "is_relevant": classification.get("is_relevant"),
        "ceew_area": classification.get("ceew_area"),
        "rationale": classification.get("rationale"),
        "confidence": classification.get("confidence"),
        "scorer_model": classification.get("scorer_model"),
    }, now_iso())


def run():
    db.init_db()

    with db.get_conn() as conn:
        # 1. Google Trends: real-time trending queries for India
        for item in serpapi_client.fetch_trending_now():
            _classify_and_store(
                conn, "google_trends", f"gtrends-now:{item['query']}", item["query"], None,
                "trending now", None, None,
            )

        # 2. Google Trends: interest-over-time for the curated CEEW keyword list
        for area, keywords in CEEW_AREA_KEYWORDS.items():
            for kw in keywords:
                result = serpapi_client.fetch_interest_over_time(kw)
                if result is None:
                    continue
                _classify_and_store(
                    conn, "google_trends", f"gtrends-interest:{kw}", kw, None,
                    "search interest (0-100)", result["latest_value"], kw,
                    context=f"trend vs 30d ago: {result['trend_pct']}%",
                )

        # 3. Reddit: search each subreddit for each seed keyword (capped to
        # keep run time and API calls reasonable)
        for kw in ALL_SEED_KEYWORDS[:10]:
            for subreddit in SUBREDDITS:
                for post in reddit_client.search_subreddit(subreddit, kw, limit=5):
                    _classify_and_store(
                        conn, "reddit", f"reddit:{post['id']}", post["title"], post["url"],
                        "upvotes", float(post["score"]), kw, context=post.get("selftext"),
                    )

        # 4. YouTube: search for each seed keyword
        for kw in ALL_SEED_KEYWORDS[:10]:
            for video in youtube_client.search_videos(kw):
                _classify_and_store(
                    conn, "youtube", f"youtube:{video['video_id']}", video["title"], video["url"],
                    "channel", None, kw, context=video.get("description"),
                )

    export_json()


def export_json():
    with db.get_conn() as conn:
        rows = db.recent_trending_items(conn)

    items = [dict(r) for r in rows]
    for d in items:
        d["is_relevant"] = bool(d.get("is_relevant"))

    SITE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_DATA_PATH, "w") as f:
        json.dump({"generated_at": now_iso(), "items": items}, f, indent=2, ensure_ascii=False)
    logger.info("Exported %d trending items to %s", len(items), SITE_DATA_PATH)


if __name__ == "__main__":
    run()
