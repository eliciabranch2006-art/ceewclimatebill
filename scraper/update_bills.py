"""
Entry point for the scheduled update job (run by
.github/workflows/update-bills.yml, or manually with `python update_bills.py`).

Flow:
  1. Fetch the current bill listing from PRS (title, url, status)
  2. For any bill not yet in the DB, or whose status has changed since
     last scrape, fetch the full detail page
  3. Score newly-added or status-changed bills (skipping any with a
     manual override)
  4. Apply overrides.json (always re-applied, so an edit takes effect
     on the next run without needing a re-scrape)
  5. Export everything to site/data/bills.json for the Next.js frontend

Run with:
    ANTHROPIC_API_KEY=sk-... python update_bills.py
    python update_bills.py --skip-scoring   # scrape only, e.g. for a first dry run
    python update_bills.py --year 2026      # limit scraping to one year, for faster iteration
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import db
import overrides as overrides_module
import prs_client
from scorer import score_bill

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SITE_DATA_PATH = Path(__file__).resolve().parent.parent / "site" / "data" / "bills.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(year: int | None, skip_scoring: bool, limit: int | None):
    db.init_db()
    listings = prs_client.fetch_bill_listing(year=year)
    if limit:
        listings = listings[:limit]
    logger.info("Fetched %d bill listings", len(listings))

    scored_count = 0
    with db.get_conn() as conn:
        for summary in listings:
            existing = conn.execute(
                "SELECT status FROM bills WHERE id = ?", (summary.id,)
            ).fetchone()
            status_changed = existing is not None and existing["status"] != summary.status
            is_new = existing is None

            if not (is_new or status_changed):
                continue  # nothing to do — already scraped and status is unchanged

            detail = prs_client.fetch_bill_detail(summary)
            bill_dict = {
                "id": detail.id,
                "title": detail.title,
                "prs_url": detail.prs_url,
                "ministry": detail.ministry,
                "prs_category": detail.prs_category,
                "status": detail.status,
                "year": detail.year,
                "highlights_text": detail.highlights_text,
                "key_issues_text": detail.key_issues_text,
                "status_timeline_json": json.dumps(detail.status_timeline),
                "bill_pdf_url": detail.bill_pdf_url,
            }
            db.upsert_bill(conn, bill_dict, now_iso())

            if not skip_scoring and db.bill_needs_scoring(conn, detail.id) or (
                not skip_scoring and status_changed
            ):
                score = score_bill(bill_dict)
                if score:
                    db.upsert_score(conn, detail.id, score, now_iso(), score["scorer_model"])
                    scored_count += 1

        overrides_module.apply_overrides(conn, now_iso())

    logger.info("Scored %d bills this run", scored_count)
    export_json()


def export_json():
    with db.get_conn() as conn:
        rows = db.all_bills_with_scores(conn)

    bills = []
    for row in rows:
        d = dict(row)
        d["status_timeline"] = json.loads(d.pop("status_timeline_json") or "[]")
        d["sectoral_secondary_areas"] = json.loads(d.pop("sectoral_secondary_areas") or "[]")
        d["needs_review"] = bool(d.get("needs_review"))
        d["is_manual_override"] = bool(d.get("is_manual_override"))
        bills.append(d)

    SITE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_DATA_PATH, "w") as f:
        json.dump(
            {"generated_at": now_iso(), "source": "PRS Legislative Research (CC BY 4.0)", "bills": bills},
            f, indent=2, ensure_ascii=False,
        )
    logger.info("Exported %d bills to %s", len(bills), SITE_DATA_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None, help="Limit scraping to one year")
    parser.add_argument("--skip-scoring", action="store_true", help="Scrape only, don't call the scorer")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of bills processed (for testing)")
    args = parser.parse_args()
    run(year=args.year, skip_scoring=args.skip_scoring, limit=args.limit)
