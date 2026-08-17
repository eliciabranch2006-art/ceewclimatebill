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
    overview_text       TEXT,               -- intro paragraphs before "Highlights of the Bill"
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
    highlights_bullets      TEXT,           -- JSON list of succinct bullet points
    issues_bullets          TEXT,           -- JSON list of succinct bullet points
    scored_at               TEXT NOT NULL,
    scorer_model            TEXT NOT NULL,  -- e.g. "claude-sonnet-5", for auditability
    prompt_version          INTEGER DEFAULT 0,  -- see scorer.PROMPT_VERSION; lets a rubric
                                                  -- change auto-trigger re-scoring
    climate_direction          TEXT,           -- 'supportive' | 'harmful' | 'mixed' | 'neutral'
    climate_direction_rationale TEXT,
    is_manual_override      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trending_items (
    id              TEXT PRIMARY KEY,   -- source-prefixed id, e.g. "gtrends:solar power india"
    source          TEXT NOT NULL,      -- 'google_trends' | 'reddit' | 'youtube'
    title           TEXT NOT NULL,      -- the query / post title / video title
    url             TEXT,
    metric_label    TEXT,               -- e.g. "search interest", "upvotes", "views context"
    metric_value    REAL,
    seed_keyword    TEXT,               -- which keyword search surfaced this item
    is_relevant     INTEGER,
    ceew_area       TEXT,
    rationale       TEXT,
    confidence      TEXT,
    scorer_model    TEXT,
    fetched_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_entries (
    id                  TEXT PRIMARY KEY,
    house               TEXT NOT NULL,   -- "Lok Sabha" | "Rajya Sabha"
    question_number     TEXT,
    question_type       TEXT,            -- Starred / Unstarred
    title               TEXT NOT NULL,
    member_name         TEXT,
    member_constituency TEXT,            -- e.g. "Kota-Bundi, Rajasthan" — best-effort
    ministry            TEXT,
    listed_date         TEXT,            -- scheduled/actual answer date (see sansad_client.py)
    question_text       TEXT,
    answer_text         TEXT,
    is_answered         INTEGER DEFAULT 0,
    url                 TEXT,
    is_relevant         INTEGER,
    ceew_area           TEXT,
    summary_bullets     TEXT,            -- JSON list of strings
    rationale           TEXT,
    confidence          TEXT,
    scorer_model        TEXT,
    is_manual_override  INTEGER DEFAULT 0,
    first_seen_at       TEXT NOT NULL,
    last_scraped_at     TEXT NOT NULL
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
        # Migration for DBs created before prompt_version existed — CREATE
        # TABLE IF NOT EXISTS above only applies to brand-new DBs, so an
        # already-committed data/bills.db needs this column added by hand.
        try:
            conn.execute("ALTER TABLE bill_scores ADD COLUMN prompt_version INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # column already exists
        try:
            conn.execute("ALTER TABLE bill_scores ADD COLUMN climate_direction TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE bill_scores ADD COLUMN climate_direction_rationale TEXT")
        except sqlite3.OperationalError:
            pass
        for col, coltype in [
            ("member_constituency", "TEXT"), ("listed_date", "TEXT"),
            ("answer_text", "TEXT"), ("is_answered", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE qa_entries ADD COLUMN {col} {coltype}")
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute("ALTER TABLE bills ADD COLUMN overview_text TEXT")
        except sqlite3.OperationalError:
            pass


def upsert_bill(conn, bill: dict, now_iso: str):
    existing = conn.execute("SELECT id FROM bills WHERE id = ?", (bill["id"],)).fetchone()
    if existing:
        conn.execute(
            """UPDATE bills SET title=?, prs_url=?, ministry=?, prs_category=?, status=?,
               year=?, overview_text=?, highlights_text=?, key_issues_text=?, status_timeline_json=?,
               bill_pdf_url=?, last_scraped_at=? WHERE id=?""",
            (bill["title"], bill["prs_url"], bill.get("ministry"), bill.get("prs_category"),
             bill.get("status"), bill.get("year"), bill.get("overview_text"), bill.get("highlights_text"),
             bill.get("key_issues_text"), bill.get("status_timeline_json"),
             bill.get("bill_pdf_url"), now_iso, bill["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO bills (id, title, prs_url, ministry, prs_category, status, year,
               overview_text, highlights_text, key_issues_text, status_timeline_json, bill_pdf_url,
               first_seen_at, last_scraped_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (bill["id"], bill["title"], bill["prs_url"], bill.get("ministry"),
             bill.get("prs_category"), bill.get("status"), bill.get("year"), bill.get("overview_text"),
             bill.get("highlights_text"), bill.get("key_issues_text"),
             bill.get("status_timeline_json"), bill.get("bill_pdf_url"), now_iso, now_iso),
        )
    return existing is not None  # True if this was an update to a bill we'd already scraped


def bill_needs_scoring(conn, bill_id: str, current_prompt_version: int) -> bool:
    """Score a bill if: it has no score yet, OR it hasn't been manually
    overridden and was scored under an older rubric version than the one
    currently in scorer.py (so rubric/prompt changes automatically catch
    up on already-scraped bills, not just newly-scraped ones)."""
    row = conn.execute(
        "SELECT is_manual_override, prompt_version FROM bill_scores WHERE bill_id = ?", (bill_id,)
    ).fetchone()
    if row is None:
        return True
    if row["is_manual_override"]:
        return False
    return (row["prompt_version"] or 0) < current_prompt_version


def upsert_score(conn, bill_id: str, score: dict, now_iso: str, model_name: str, prompt_version: int):
    conn.execute(
        """INSERT INTO bill_scores (bill_id, sectoral_primary_area, sectoral_secondary_areas,
           sectoral_score, mitigation_score, enforceability_score, scale_score, novelty_score,
           total_score, rationale, confidence, needs_review, highlights_bullets, issues_bullets,
           scored_at, scorer_model, prompt_version, climate_direction, climate_direction_rationale,
           is_manual_override)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
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
             highlights_bullets=excluded.highlights_bullets,
             issues_bullets=excluded.issues_bullets,
             scored_at=excluded.scored_at,
             scorer_model=excluded.scorer_model,
             prompt_version=excluded.prompt_version,
             climate_direction=excluded.climate_direction,
             climate_direction_rationale=excluded.climate_direction_rationale
           WHERE bill_scores.is_manual_override = 0""",
        (bill_id, score.get("sectoral_primary_area"), score.get("sectoral_secondary_areas_json"),
         score.get("sectoral_score"), score.get("mitigation_score"), score.get("enforceability_score"),
         score.get("scale_score"), score.get("novelty_score"), score.get("total_score"),
         score.get("rationale"), score.get("confidence"), score.get("needs_review"),
         score.get("highlights_bullets_json"), score.get("issues_bullets_json"),
         now_iso, model_name, prompt_version,
         score.get("climate_direction"), score.get("climate_direction_rationale")),
    )


def upsert_trending_item(conn, item: dict, now_iso: str):
    conn.execute(
        """INSERT INTO trending_items (id, source, title, url, metric_label, metric_value,
           seed_keyword, is_relevant, ceew_area, rationale, confidence, scorer_model, fetched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             metric_value=excluded.metric_value, metric_label=excluded.metric_label,
             is_relevant=excluded.is_relevant, ceew_area=excluded.ceew_area,
             rationale=excluded.rationale, confidence=excluded.confidence,
             scorer_model=excluded.scorer_model, fetched_at=excluded.fetched_at""",
        (item["id"], item["source"], item["title"], item.get("url"), item.get("metric_label"),
         item.get("metric_value"), item.get("seed_keyword"), int(item.get("is_relevant") or 0),
         item.get("ceew_area"), item.get("rationale"), item.get("confidence"),
         item.get("scorer_model"), now_iso),
    )


def recent_trending_items(conn, max_age_days: int = 14):
    return conn.execute(
        """SELECT * FROM trending_items
           WHERE datetime(fetched_at) >= datetime('now', ?)
           ORDER BY is_relevant DESC, metric_value DESC""",
        (f"-{max_age_days} days",),
    ).fetchall()


def upsert_qa_entry(conn, entry: dict, now_iso: str):
    existing = conn.execute("SELECT id, is_manual_override FROM qa_entries WHERE id = ?",
                             (entry["id"],)).fetchone()
    if existing and existing["is_manual_override"]:
        # still refresh last_scraped_at so we know it was checked, but leave
        # classification fields alone
        conn.execute("UPDATE qa_entries SET last_scraped_at=? WHERE id=?",
                      (now_iso, entry["id"]))
        return
    if existing:
        conn.execute(
            """UPDATE qa_entries SET house=?, question_number=?, question_type=?, title=?,
               member_name=?, member_constituency=?, ministry=?, listed_date=?, question_text=?,
               answer_text=?, is_answered=?, url=?, is_relevant=?, ceew_area=?, summary_bullets=?,
               rationale=?, confidence=?, scorer_model=?, last_scraped_at=? WHERE id=?""",
            (entry["house"], entry.get("question_number"), entry.get("question_type"),
             entry["title"], entry.get("member_name"), entry.get("member_constituency"),
             entry.get("ministry"), entry.get("listed_date"), entry.get("question_text"),
             entry.get("answer_text"), int(entry.get("is_answered") or 0), entry.get("url"),
             int(entry.get("is_relevant") or 0), entry.get("ceew_area"),
             entry.get("summary_bullets_json"), entry.get("rationale"), entry.get("confidence"),
             entry.get("scorer_model"), now_iso, entry["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO qa_entries (id, house, question_number, question_type, title,
               member_name, member_constituency, ministry, listed_date, question_text,
               answer_text, is_answered, url, is_relevant, ceew_area,
               summary_bullets, rationale, confidence, scorer_model, first_seen_at, last_scraped_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (entry["id"], entry["house"], entry.get("question_number"), entry.get("question_type"),
             entry["title"], entry.get("member_name"), entry.get("member_constituency"),
             entry.get("ministry"), entry.get("listed_date"), entry.get("question_text"),
             entry.get("answer_text"), int(entry.get("is_answered") or 0), entry.get("url"),
             int(entry.get("is_relevant") or 0), entry.get("ceew_area"),
             entry.get("summary_bullets_json"), entry.get("rationale"), entry.get("confidence"),
             entry.get("scorer_model"), now_iso, now_iso),
        )


def all_qa_entries(conn):
    return conn.execute(
        "SELECT * FROM qa_entries ORDER BY listed_date DESC"
    ).fetchall()


def get_qa_entry_status(conn, entry_id: str):
    """Returns a row with is_answered/is_manual_override for one entry, or
    None if it hasn't been scraped yet. Used to decide whether an already-
    seen-but-unanswered question should be re-checked for a new answer."""
    return conn.execute(
        "SELECT is_answered, is_manual_override FROM qa_entries WHERE id = ?", (entry_id,)
    ).fetchone()


def all_bills_with_scores(conn):
    return conn.execute(
        """SELECT b.*, s.sectoral_primary_area, s.sectoral_secondary_areas, s.sectoral_score,
                  s.mitigation_score, s.enforceability_score, s.scale_score, s.novelty_score,
                  s.total_score, s.rationale, s.confidence, s.needs_review,
                  s.highlights_bullets, s.issues_bullets, s.scored_at,
                  s.scorer_model, s.is_manual_override, s.climate_direction,
                  s.climate_direction_rationale
           FROM bills b LEFT JOIN bill_scores s ON b.id = s.bill_id
           ORDER BY s.total_score DESC NULLS LAST, b.year DESC"""
    ).fetchall()
