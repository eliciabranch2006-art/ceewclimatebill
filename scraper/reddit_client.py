"""
Reddit search via PRAW, in read-only mode — no user login needed, just a
free "app" registered at reddit.com/prefs/apps (choose type "script"),
which gives you a client ID and secret.

Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET as environment
variables / GitHub secrets.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _get_reddit():
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not (client_id and client_secret):
        logger.warning("REDDIT_CLIENT_ID/SECRET not set — skipping Reddit")
        return None

    import praw  # imported lazily so the module can be imported without praw installed

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="CEEW-ClimateTrendsTracker/0.1 (research tool)",
    )


def search_subreddit(subreddit_name: str, query: str, limit: int = 10) -> list[dict]:
    """Search one subreddit for a query, return recent/relevant posts."""
    reddit = _get_reddit()
    if reddit is None:
        return []

    results = []
    try:
        for post in reddit.subreddit(subreddit_name).search(query, sort="relevance", time_filter="month", limit=limit):
            results.append({
                "id": post.id,
                "title": post.title,
                "url": f"https://reddit.com{post.permalink}",
                "subreddit": subreddit_name,
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": post.created_utc,
                "selftext": (post.selftext or "")[:500],
            })
    except Exception:
        logger.exception("Reddit search failed for r/%s q=%r", subreddit_name, query)
    return results
