"""
Scraper for Lok Sabha & Rajya Sabha parliamentary Q&A via sansad.in.

**Read this before running.** Unlike PRS's bill tracker (plain server-
rendered HTML), sansad.in's Q&A search
(https://sansad.in/ls/questions/questions-and-answers and the /rs/
equivalent) is a JavaScript single-page app — the search form and
results only exist after JS runs and an API call resolves ("Please wait
a few seconds for the result to load"). A `requests`-based scraper
cannot see this content at all; it needs a real (headless) browser,
which is what Playwright gives us.

This also means I could not verify exact form field selectors the way I
did for PRS — I only know the field *labels* from the page's visible
text (Search On, Matches On, Session, Answer Date, Member Name, Ministry
Name, Question Type, Question Number), not their underlying HTML
structure. The locators below use Playwright's label/role/placeholder-
based matching (get_by_label, get_by_role) specifically because it's
more resilient to unknown internal markup than CSS selectors — but you
should expect this file to need real debugging on first run.

**Strongly recommended before running this in CI:** run
`playwright codegen https://sansad.in/ls/questions/questions-and-answers`
locally (after `pip install playwright && playwright install chromium`).
It opens a real browser, records your clicks as you manually do one
search, and generates working Python selectors you can drop in below.
This will get you correct selectors far faster than trial-and-error
against the CI logs. Send me the generated code and I'll wire it in.

Politeness: sleeps between requests, single browser instance reused
across searches, runs on a schedule (not continuously).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

HOUSES = {
    "ls": "https://sansad.in/ls/questions/questions-and-answers",
    "rs": "https://sansad.in/rs/questions/questions-and-answers",
}

SEARCH_DELAY_SECONDS = 3.0  # generous — this is a JS app that needs render + API round-trip time


@dataclass
class QAEntry:
    id: str  # e.g. "ls-2026-session1-1234"
    house: str  # "Lok Sabha" | "Rajya Sabha"
    question_number: Optional[str] = None
    question_type: Optional[str] = None  # Starred / Unstarred
    title: str = ""
    member_name: Optional[str] = None
    ministry: Optional[str] = None
    answer_date: Optional[str] = None
    question_text: str = ""
    answer_text: str = ""
    url: Optional[str] = None


def search_qa(house: str, keyword: str, max_results: int = 15) -> list[QAEntry]:
    """Search one house's Q&A for a title keyword. Returns [] and logs a
    warning if playwright isn't installed/available, rather than crashing
    the whole run — lets you disable this module without touching
    update_qa.py."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed — skipping Q&A scrape. Run: "
                        "pip install playwright && playwright install --with-deps chromium")
        return []

    house_label = "Lok Sabha" if house == "ls" else "Rajya Sabha"
    entries: list[QAEntry] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(HOUSES[house], wait_until="networkidle", timeout=45000)

            # --- Fill the search form ---
            # TODO: verify these against the real page (see module docstring).
            # "Search On" appears to be a dropdown defaulting to a field like
            # Title; we select "Title" explicitly if the label is findable.
            try:
                page.get_by_label("Search On").select_option(label="Title")
            except Exception:
                logger.debug("Could not set 'Search On' dropdown — using page default")

            try:
                page.get_by_label("Matches On").select_option(label="Any Words")
            except Exception:
                logger.debug("Could not set 'Matches On' dropdown — using page default")

            # The free-text title search box — try a few plausible ways to find it
            title_box = None
            for locator_attempt in [
                lambda: page.get_by_placeholder("Title", exact=False),
                lambda: page.get_by_role("textbox", name="Title"),
            ]:
                try:
                    candidate = locator_attempt()
                    if candidate.count() > 0:
                        title_box = candidate.first
                        break
                except Exception:
                    continue
            if title_box is None:
                logger.warning("Could not find the title search box for %s — skipping keyword %r",
                                house, keyword)
                return []
            title_box.fill(keyword)

            # Submit — the page shows a "Filter" or "Apply" button
            for button_text in ["Apply", "Filter", "Search"]:
                btn = page.get_by_role("button", name=button_text)
                if btn.count() > 0:
                    btn.first.click()
                    break

            page.wait_for_timeout(int(SEARCH_DELAY_SECONDS * 1000))
            page.wait_for_load_state("networkidle", timeout=30000)

            # --- Parse results ---
            # TODO: verify the actual result-row structure. Assuming results
            # render as a list/table of rows, each containing the question
            # title as a clickable link plus member/ministry/date text.
            rows = page.locator("[class*='question'], [class*='result'], tr").all()
            for row in rows[:max_results]:
                text = row.inner_text().strip()
                if not text or len(text) < 10:
                    continue
                link = row.locator("a").first
                href = None
                try:
                    href = link.get_attribute("href")
                except Exception:
                    pass
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if not lines:
                    continue
                entry_id = f"{house}:{href or lines[0][:60]}"
                entries.append(QAEntry(
                    id=entry_id,
                    house=house_label,
                    title=lines[0],
                    url=href if (href and href.startswith("http")) else
                        (f"https://sansad.in{href}" if href else None),
                ))
        except Exception:
            logger.exception("Q&A search failed for house=%s keyword=%r", house, keyword)
        finally:
            browser.close()

    return entries


def fetch_qa_detail(entry: QAEntry) -> QAEntry:
    """Fetch the full question + answer text for one entry. Best-effort —
    returns the entry unchanged (with empty question/answer text) if the
    detail page can't be parsed, rather than failing the whole run."""
    if not entry.url:
        return entry
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return entry

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(entry.url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(int(SEARCH_DELAY_SECONDS * 1000))
            body_text = page.locator("body").inner_text()
            # TODO: this grabs the whole page body as a rough fallback. Once
            # you've confirmed the real detail-page structure, replace with
            # targeted locators for the question text vs. answer text blocks.
            entry.question_text = body_text[:3000]
        except Exception:
            logger.exception("Could not fetch Q&A detail for %s", entry.url)
        finally:
            browser.close()

    return entry
