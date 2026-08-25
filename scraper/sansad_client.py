"""
Scraper for Lok Sabha & Rajya Sabha parliamentary Q&A via sansad.in.

**Verified against the real site** (2026-08) via two rounds of playwright
codegen:
  - Search: click #input-with-icon-textfield, fill with the query, press
    Enter.
  - Results render as a table (role="row" per result, role="cell" for
    content). Critically, there is NO separate detail page per question —
    clicking a row's "expand row" control (get_by_label("expand row"))
    reveals the full question/answer INLINE, on the same page. This means
    the whole search+detail flow for a keyword happens in ONE page load,
    not one load per result — a big win given this site's confirmed
    2-3+ minute load times.
  - A row's accessible name looks like "356 Roadmap to Accelerate..." —
    a leading question number followed by the title.

**Still unverified**: the exact DOM boundary of what text appears once a
row is expanded (member name, ministry, constituency, answer text) — the
extraction below captures the row's expanded text as a whole and applies
best-effort parsing on top. If that parsing misbehaves, the fix is the
same as before: run `playwright codegen`, expand one row, and note
exactly what appears so the specific fields (not just the raw text) can
be targeted directly.

Performance: one browser is reused for the whole run via SansadSession.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

HOUSES = {
    "ls": "https://sansad.in/ls/questions/questions-and-answers",
    "rs": "https://sansad.in/rs/questions/questions-and-answers",
}

# Confirmed by hand: 2-3+ minutes to load, nothing to do with Playwright.
NAV_TIMEOUT_MS = 240000
RENDER_PAUSE_SECONDS = 5.0
EXPAND_PAUSE_SECONDS = 2.0  # shorter — this is an in-page interaction, not a full reload


@dataclass
class QAEntry:
    id: str
    house: str  # "Lok Sabha" | "Rajya Sabha"
    question_number: Optional[str] = None
    question_type: Optional[str] = None
    title: str = ""
    member_name: Optional[str] = None
    member_constituency: Optional[str] = None
    ministry: Optional[str] = None
    listed_date: Optional[str] = None
    question_text: str = ""
    answer_text: str = ""
    url: Optional[str] = None

    @property
    def is_answered(self) -> bool:
        return bool(self.answer_text.strip())


class SansadSession:
    """Wraps a single reused Playwright browser for the whole scrape run.

        with SansadSession() as session:
            entries = session.search_and_expand("ls", "renewable energy")
    """

    def __init__(self):
        self._playwright = None
        self._browser = None

    def __enter__(self) -> "SansadSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright not installed — Q&A scraping will no-op. Run: "
                            "pip install playwright && playwright install --with-deps chromium")
            return self
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        return self

    def __exit__(self, *exc_info):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    @property
    def available(self) -> bool:
        return self._browser is not None

    def search_and_expand(self, house: str, keyword: str, max_results: int = 10) -> list[QAEntry]:
        """Searches for `keyword`, then expands each result row in place to
        pull its full detail — all in one page load. Replaces the older
        two-phase search-then-navigate-to-detail-page approach, which
        doesn't match how this site actually works (see module docstring).
        """
        if not self.available:
            return []

        house_label = "Lok Sabha" if house == "ls" else "Rajya Sabha"
        entries: list[QAEntry] = []
        page = self._browser.new_page()
        try:
            page.goto(HOUSES[house], wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            page.wait_for_timeout(int(RENDER_PAUSE_SECONDS * 1000))

            search_box = page.locator("#input-with-icon-textfield")
            search_box.click()
            search_box.fill(keyword)
            search_box.press("Enter")
            page.wait_for_timeout(int(RENDER_PAUSE_SECONDS * 1000))

            rows = page.get_by_role("row").all()
            processed = 0
            for row in rows:
                if processed >= max_results:
                    break
                try:
                    row_text_before = row.inner_text().strip()
                except Exception:
                    continue
                if not row_text_before or len(row_text_before) < 5:
                    continue  # skip empty/header rows

                # Leading question number, e.g. "356 Roadmap to Accelerate..."
                number_match = re.match(r"^\s*(\d+)\s+(.*)", row_text_before, re.DOTALL)
                question_number = number_match.group(1) if number_match else None
                title = (number_match.group(2) if number_match else row_text_before).strip()
                title = title.split("\n")[0][:300]  # first line only, capped

                entry_id = f"{house}:{question_number or title[:60]}"

                expand_control = row.get_by_label("expand row")
                if expand_control.count() == 0:
                    # No expand control on this row — likely a header or
                    # non-question row. Skip rather than guess.
                    continue

                try:
                    expand_control.first.click()
                    page.wait_for_timeout(int(EXPAND_PAUSE_SECONDS * 1000))
                    expanded_text = row.inner_text().strip()
                except Exception:
                    logger.exception("Could not expand row for %r", title)
                    expanded_text = row_text_before

                # The newly revealed content is whatever wasn't in the row
                # before expansion — a heuristic, but grounded in a
                # confirmed real interaction rather than pure guesswork.
                new_content = expanded_text
                if expanded_text.startswith(row_text_before):
                    new_content = expanded_text[len(row_text_before):].strip()

                entry = QAEntry(
                    id=entry_id,
                    house=house_label,
                    question_number=question_number,
                    title=title,
                )
                self._apply_expanded_text(entry, new_content or expanded_text)
                entries.append(entry)
                processed += 1

        except Exception:
            logger.exception("Q&A search failed for house=%s keyword=%r", house, keyword)
        finally:
            page.close()

        return entries

    @staticmethod
    def _apply_expanded_text(entry: QAEntry, text: str) -> None:
        """Best-effort field extraction from the expanded row's text.
        TODO: replace with targeted locators once you've confirmed the
        exact structure of expanded content (see module docstring)."""
        entry.question_text = text[:3000]

        lower = text.lower()
        answer_idx = lower.find("answer")
        if answer_idx != -1:
            entry.question_text = text[:answer_idx].strip()[:3000]
            entry.answer_text = text[answer_idx:].strip()[:3000]

        ministry_match = re.search(r"ministry\s*:?\s*([^\n]+)", text, re.IGNORECASE)
        if ministry_match:
            entry.ministry = ministry_match.group(1).strip()[:200]

        member_match = re.search(r"(?:member|asked by|shri|smt\.?)\s*:?\s*([^\n]+)", text, re.IGNORECASE)
        if member_match:
            entry.member_name = member_match.group(1).strip()[:200]

        date_match = re.search(
            r"(?:date of answer|answer date|listed for)\D{0,20}"
            r"([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})",
            text, re.IGNORECASE,
        )
        if date_match:
            entry.listed_date = date_match.group(1)


# Backwards-compatible single-call helper.
def search_and_expand(house: str, keyword: str, max_results: int = 10) -> list[QAEntry]:
    with SansadSession() as session:
        return session.search_and_expand(house, keyword, max_results)
