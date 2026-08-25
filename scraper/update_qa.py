"""
Entry point for the Q&A update job (run by
.github/workflows/update-qa.yml, or manually with `python update_qa.py`).

Searches both houses' Q&A archives for CEEW-relevant seed keywords
(reusing the same keyword list as the trends module), fetches full text
for new results, classifies with Claude, stores in SQLite, and exports
site/data/qa.json.

Unlike bills (which are stable once passed), a Q&A entry can start
unanswered and get its answer added later — so unlike a bill, we don't
just skip every already-seen entry. Only entries that are ALREADY
answered (or manually corrected) are treated as finished/immutable;
anything still awaiting an answer gets re-checked on every run so the
countdown/overdue state and the eventual answer text actually update.

Given sansad_client.py's scraping is best-effort against a JS-rendered
site (see its docstring), this script treats scraping failures as
non-fatal — it logs and moves to the next keyword/house rather than
crashing the whole run.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import db
import sansad_client
from qa_scorer import classify_qa
from trend_keywords import ALL_SEED_KEYWORDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
    if not entries:
        entries = [{
            "id": "placeholder-empty-export", "house": "Lok Sabha", "question_number": None,
            "question_type": None, "title": "No Q&A entries currently match the tracker's criteria",
            "member_name": None, "member_constituency": None, "ministry": None, "listed_date": None,
            "question_text": None, "answer_text": None, "is_answered": False, "url": None,
            "is_relevant": False, "ceew_area": None, "summary_bullets": [], "rationale": None,
            "confidence": None, "scorer_model": None, "is_manual_override": False,
            "first_seen_at": now_iso(), "last_scraped_at": now_iso(),
        }]
SITE_DATA_PATH = Path(__file__).resolve().parent.parent / "site" / "data" / "qa.json"

# Keep this small at first — each keyword triggers a real browser search
# (now reusing one browser for the whole run — see SansadSession) and
# each new result triggers a Claude API call. Expand once you've
# confirmed the scraper selectors actually work.
KEYWORDS_PER_RUN = 8


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(keyword_limit: int = KEYWORDS_PER_RUN):
    db.init_db()
    keywords = ALL_SEED_KEYWORDS[:keyword_limit]
    classified_count = 0

    # One browser for the entire run (see sansad_client.SansadSession) —
    # the original version launched a fresh browser per search AND per
    # detail fetch, which is most of why the first run took 15+ minutes.
    with db.get_conn() as conn, sansad_client.SansadSession() as session:
        if not session.available:
            logger.warning("Playwright unavailable — Q&A run will find nothing this time")

        for house in ("ls", "rs"):
            for kw in keywords:
                results = session.search_qa(house, kw)
                logger.info("house=%s keyword=%r -> %d results", house, kw, len(results))

                for summary in results:
                    status = db.get_qa_entry_status(conn, summary.id)
                    if status is not None and (status["is_answered"] or status["is_manual_override"]):
                        continue  # finished record — answered or human-reviewed, don't touch it
                    # else: brand new, OR previously seen but still unanswered — (re)fetch

                    detail = session.fetch_qa_detail(summary)
                    entry_dict = {
                        "id": detail.id, "house": detail.house,
                        "question_number": detail.question_number,
                        "question_type": detail.question_type, "title": detail.title,
                        "member_name": detail.member_name,
                        "member_constituency": detail.member_constituency,
                        "ministry": detail.ministry, "listed_date": detail.listed_date,
                        "question_text": detail.question_text, "answer_text": detail.answer_text,
                        "is_answered": detail.is_answered, "url": detail.url,
                    }

                    classification = classify_qa(entry_dict) or {}
                    entry_dict.update({
                        "is_relevant": classification.get("is_relevant"),
                        "ceew_area": classification.get("ceew_area"),
                        "summary_bullets_json": classification.get("summary_bullets_json"),
                        "rationale": classification.get("rationale"),
                        "confidence": classification.get("confidence"),
                        "scorer_model": classification.get("scorer_model"),
                    })
                    db.upsert_qa_entry(conn, entry_dict, now_iso())
                    classified_count += 1

    logger.info("Classified/updated %d Q&A entries this run", classified_count)
    export_json()


def export_json():
    with db.get_conn() as conn:
        rows = db.all_qa_entries(conn)

    entries = []
    for row in rows:
        d = dict(row)
        d["summary_bullets"] = json.loads(d.pop("summary_bullets") or "[]")
        d["is_relevant"] = bool(d.get("is_relevant"))
        d["is_manual_override"] = bool(d.get("is_manual_override"))
        d["is_answered"] = bool(d.get("is_answered"))
        entries.append(d)

    SITE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SITE_DATA_PATH, "w") as f:
        json.dump(
            {"generated_at": now_iso(), "source": "sansad.in (Lok Sabha / Rajya Sabha)", "entries": entries},
            f, indent=2, ensure_ascii=False,
        )
    logger.info("Exported %d Q&A entries to %s", len(entries), SITE_DATA_PATH)


if __name__ == "__main__":
    run()
