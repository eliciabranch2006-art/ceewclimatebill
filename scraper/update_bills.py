"""
Entry point for the scheduled update job (run by
.github/workflows/update-bills.yml, or manually with `python update_bills.py`).

Flow:
  1. Fetch the current bill listing from PRS (title, url, status)
  2. For any bill not yet in the DB, whose status has changed, or whose
     existing score is older than the current rubric version, (re)score it
  3. Apply overrides.json (always re-applied, so an edit takes effect
     on the next run without needing a re-scrape)
  4. Export everything to site/data/bills.json for the Next.js frontend

Run with:
    ANTHROPIC_API_KEY=sk-... python update_bills.py
    python update_bills.py --skip-scoring   # scrape only, e.g. for a first dry run
    python update_bills.py --year 2026      # limit scraping to one year, for faster iteration
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import db
import overrides as overrides_module
import prs_client
from scorer import score_bill, PROMPT_VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SITE_DATA_PATH = Path(__file__).resolve().parent.parent / "site" / "data" / "bills.json"

# Per CEEW outreach team: the site should only ever show bills from the last
# 2 years. Applied twice — once early during scraping (so we don't waste time
# and Claude API cost fetching/scoring bills that will just be filtered out),
# and again at export time as a safety net.
CUTOFF_YEARS = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cutoff_year() -> int:
    return datetime.now(timezone.utc).year - CUTOFF_YEARS


def _normalize_title(title: str) -> str:
    """Lowercase, punctuation-stripped title, used only to catch duplicate
    bill entries that ended up under two different slugs."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def run(year: int | None, skip_scoring: bool, limit: int | None):
    db.init_db()
    listings = prs_client.fetch_bill_listing(year=year)
    if limit:
        listings = listings[:limit]
    logger.info("Fetched %d bill listings", len(listings))

    scored_count = 0
    skipped_old_count = 0
    cutoff_year = _cutoff_year()
    with db.get_conn() as conn:
        for summary in listings:
            title_year = prs_client._year_from_title(summary.title)
            if title_year is not None and title_year < cutoff_year:
                skipped_old_count += 1
                continue  # more than CUTOFF_YEARS old — skip fetching/scoring entirely

            existing = conn.execute(
                "SELECT * FROM bills WHERE id = ?", (summary.id,)
            ).fetchone()
            is_new = existing is None
            status_changed = (not is_new) and existing["status"] != summary.status
            needs_rescore = (not skip_scoring) and db.bill_needs_scoring(
                conn, summary.id, PROMPT_VERSION
            )

            if not (is_new or status_changed or needs_rescore):
                continue  # nothing to do — already scraped, unchanged, and current on the rubric

            if is_new or status_changed:
                # Content may have changed (or doesn't exist yet) — worth
                # re-hitting PRS for the current text.
                detail = prs_client.fetch_bill_detail(summary)
                bill_dict = {
                    "id": detail.id,
                    "title": detail.title,
                    "prs_url": detail.prs_url,
                    "ministry": detail.ministry,
                    "prs_category": detail.prs_category,
                    "status": detail.status,
                    "year": detail.year,
                    "overview_text": detail.overview_text,
                    "highlights_text": detail.highlights_text,
                    "key_issues_text": detail.key_issues_text,
                    "status_timeline_json": json.dumps(detail.status_timeline),
                    "bill_pdf_url": detail.bill_pdf_url,
                }
                db.upsert_bill(conn, bill_dict, now_iso())
            else:
                # Rescore-only path (rubric changed, bill content hasn't) —
                # reuse what's already in the DB instead of re-scraping PRS.
                bill_dict = {
                    "id": existing["id"], "title": existing["title"],
                    "prs_url": existing["prs_url"], "ministry": existing["ministry"],
                    "prs_category": existing["prs_category"], "status": existing["status"],
                    "year": existing["year"], "overview_text": existing["overview_text"],
                    "highlights_text": existing["highlights_text"],
                    "key_issues_text": existing["key_issues_text"],
                }

            if not skip_scoring and (is_new or status_changed or needs_rescore):
                score = score_bill(bill_dict)
                if score:
                    db.upsert_score(conn, summary.id, score, now_iso(), score["scorer_model"], PROMPT_VERSION)
                    scored_count += 1

        overrides_module.apply_overrides(conn, now_iso())

    logger.info("Scored %d bills this run (skipped %d bills older than %d)",
                scored_count, skipped_old_count, cutoff_year)
    export_json()


def export_json():
    with db.get_conn() as conn:
        rows = db.all_bills_with_scores(conn)

    cutoff_year = _cutoff_year()
    best_by_title: dict[str, dict] = {}
    for row in rows:
        d = dict(row)
        if d.get("year") is not None and d["year"] < cutoff_year:
            continue  # safety-net filter — see CUTOFF_YEARS comment above
        d["status_timeline"] = json.loads(d.pop("status_timeline_json") or "[]")
        d["sectoral_secondary_areas"] = json.loads(d.pop("sectoral_secondary_areas") or "[]")
        d["highlights_bullets"] = json.loads(d.pop("highlights_bullets") or "[]")
        d["issues_bullets"] = json.loads(d.pop("issues_bullets") or "[]")
        d["needs_review"] = bool(d.get("needs_review"))
        d["is_manual_override"] = bool(d.get("is_manual_override"))
        d["auto_flagged"] = bool(d.get("auto_flagged"))

        # Dedup safety net: if the same bill ended up under two different
        # slugs, keep whichever copy is actually classified over one that's
        # null, and among equally-classified copies keep the more recent.
        key = _normalize_title(d["title"])
        existing = best_by_title.get(key)
        if existing is None:
            best_by_title[key] = d
        else:
            existing_classified = existing.get("sectoral_primary_area") is not None
            new_classified = d.get("sectoral_primary_area") is not None
            if new_classified and not existing_classified:
                best_by_title[key] = d
            elif new_classified == existing_classified and \
                    d.get("last_scraped_at", "") > existing.get("last_scraped_at", ""):
                best_by_title[key] = d

    bills = list(best_by_title.values())

    # Next.js's static export build has a quirk where a dynamic route's
    # generateStaticParams() returning a genuinely empty array gets
    # misreported as a build error ("missing generateStaticParams") rather
    # than being treated as "zero pages, that's valid". Guard against ever
    # exporting a truly empty array, so an automated run that legitimately
    # finds zero bills can never silently break the live site.
    if not bills:
        bills = [{
            "id": "placeholder-empty-export", "title": "No bills currently match the tracker's criteria",
            "prs_url": "https://prsindia.org/billtrack", "ministry": None, "prs_category": None,
            "status": None, "year": None, "overview_text": None, "highlights_text": None,
            "key_issues_text": None, "status_timeline": [], "bill_pdf_url": None,
            "first_seen_at": now_iso(), "last_scraped_at": now_iso(),
            "sectoral_primary_area": None, "sectoral_secondary_areas": [], "sectoral_score": None,
            "mitigation_score": None, "enforceability_score": None, "scale_score": None,
            "novelty_score": None, "total_score": None, "rationale": None, "confidence": None,
            "needs_review": False, "highlights_bullets": [], "issues_bullets": [],
            "scored_at": None, "scorer_model": None, "is_manual_override": False,
            "climate_direction": None, "climate_direction_rationale": None, "auto_flagged": False,
        }]

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
