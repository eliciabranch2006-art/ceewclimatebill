"""
SQLite storage for the bills module.

Design choice: SQLite file committed to the repo (data/bills.db). For a
small team this avoids running/paying for a database server — GitHub
Actions checks out the repo, updates the file, and commits it back.
If the dataset outgrows SQLite (unlikely for parliamentary bill volumes:
low hundreds per year), swap this module for a hosted Postgres client
(e.g. Supabase) without changing the calling code much.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bills.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bills (
    id                  TEXT PRIMARY KEY,   -- slug from the PRS URL, stable identifier
    title               TEXT NOT NULL,
    prs_url             TEXT NOT NULL,
    ministry            TEXT,
    prs_category        TEXT,               -- PRS's own 7-way category (Infrastructure and Environment, etc.)
    status              TEXT,               -- Passed / Pending / In Committee / Lapsed / Withdrawn / etc.
    year                INTEGER,
    highlights_text     TEXT,               -- "Highlights of the Bill" section, scraped
    key_issues_text     TEXT,               -- "Key Issues and Analysis" section, scraped
    status_timeline_json TEXT,              -- JSON list of {stage, chamber, date}
    bill_pdf_url        TEXT,
    first_seen_at       TEXT NOT NULL,
    last_scraped_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bill_scores (
    bill_id                 TEXT PRIMARY KEY REFERENCES bills(id),
    sectoral_primary_area   TEXT,           -- one of ceew_taxonomy.ALL_AREAS
    sectoral_secondary_areas TEXT,          -- JSON list of areas
    sectoral_score          INTEGER,        -- 0-30
    mitigation_score        INTEGER,        -- 0-25
    enforceability_score    INTEGER,        -- 0-20
    scale_score             INTEGER,        -- 0-15
    novelty_score           INTEGER,        -- 0-10
    total_score             INTEGER,        -- 0-100, sum of the above
    rationale               TEXT,           -- model's plain-language justification
    confidence              TEXT,           -- "high" / "medium" / "low", from the model
    needs_review            INTEGER,        -- 1 if confidence is low or score is borderline
    scored_at               TEXT NOT NULL,
    scorer_model            TEXT NOT NULL,  -- e.g. "claude-sonnet-5", for auditability
    is_manual_override      INTEGER DEFAULT 0
);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_bill(conn, bill: dict, now_iso: str):
    existing = conn.execute("SELECT id FROM bills WHERE id = ?", (bill["id"],)).fetchone()
    if existing:
        conn.execute(
            """UPDATE bills SET title=?, prs_url=?, ministry=?, prs_category=?, status=?,
               year=?, highlights_text=?, key_issues_text=?, status_timeline_json=?,
               bill_pdf_url=?, last_scraped_at=? WHERE id=?""",
            (bill["title"], bill["prs_url"], bill.get("ministry"), bill.get("prs_category"),
             bill.get("status"), bill.get("year"), bill.get("highlights_text"),
             bill.get("key_issues_text"), bill.get("status_timeline_json"),
             bill.get("bill_pdf_url"), now_iso, bill["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO bills (id, title, prs_url, ministry, prs_category, status, year,
               highlights_text, key_issues_text, status_timeline_json, bill_pdf_url,
               first_seen_at, last_scraped_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (bill["id"], bill["title"], bill["prs_url"], bill.get("ministry"),
             bill.get("prs_category"), bill.get("status"), bill.get("year"),
             bill.get("highlights_text"), bill.get("key_issues_text"),
             bill.get("status_timeline_json"), bill.get("bill_pdf_url"), now_iso, now_iso),
        )
    return existing is not None  # True if this was an update to a bill we'd already scraped


def bill_needs_scoring(conn, bill_id: str) -> bool:
    """Score a bill if it has no score yet, or if it hasn't been manually overridden
    and its status has changed since it was last scored (status changes, e.g.
    Introduced -> Passed, can change enforceability/scale substance)."""
    row = conn.execute(
        "SELECT is_manual_override FROM bill_scores WHERE bill_id = ?", (bill_id,)
    ).fetchone()
    if row is None:
        return True
    if row["is_manual_override"]:
        return False
    return False  # re-scoring on every status change is handled by update_bills.py explicitly


def upsert_score(conn, bill_id: str, score: dict, now_iso: str, model_name: str):
    conn.execute(
        """INSERT INTO bill_scores (bill_id, sectoral_primary_area, sectoral_secondary_areas,
           sectoral_score, mitigation_score, enforceability_score, scale_score, novelty_score,
           total_score, rationale, confidence, needs_review, scored_at, scorer_model, is_manual_override)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
           ON CONFLICT(bill_id) DO UPDATE SET
             sectoral_primary_area=excluded.sectoral_primary_area,
             sectoral_secondary_areas=excluded.sectoral_secondary_areas,
             sectoral_score=excluded.sectoral_score,
             mitigation_score=excluded.mitigation_score,
             enforceability_score=excluded.enforceability_score,
             scale_score=excluded.scale_score,
             novelty_score=excluded.novelty_score,
             total_score=excluded.total_score,
             rationale=excluded.rationale,
             confidence=excluded.confidence,
             needs_review=excluded.needs_review,
             scored_at=excluded.scored_at,
             scorer_model=excluded.scorer_model
           WHERE bill_scores.is_manual_override = 0""",
        (bill_id, score.get("sectoral_primary_area"), score.get("sectoral_secondary_areas_json"),
         score.get("sectoral_score"), score.get("mitigation_score"), score.get("enforceability_score"),
         score.get("scale_score"), score.get("novelty_score"), score.get("total_score"),
         score.get("rationale"), score.get("confidence"), score.get("needs_review"),
         now_iso, model_name),
    )


def all_bills_with_scores(conn):
    return conn.execute(
        """SELECT b.*, s.sectoral_primary_area, s.sectoral_secondary_areas, s.sectoral_score,
                  s.mitigation_score, s.enforceability_score, s.scale_score, s.novelty_score,
                  s.total_score, s.rationale, s.confidence, s.needs_review, s.scored_at,
                  s.scorer_model, s.is_manual_override
           FROM bills b LEFT JOIN bill_scores s ON b.id = s.bill_id
           ORDER BY s.total_score DESC NULLS LAST, b.year DESC"""
    ).fetchall()
