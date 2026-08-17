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

**Performance note (fixed after the first version ran ~15+ minutes):**
this used to launch a brand-new browser for every single search AND
every single detail-page fetch — dozens of full browser startups per
run. It also waited for Playwright's "networkidle" state, which many
JS-heavy sites (background polling, analytics beacons) never actually
reach, silently eating the full timeout on every navigation. Fixed by:
(1) reusing ONE browser for the whole run via SansadSession below —
    only lightweight pages are opened/closed per navigation, not whole
    browsers;
(2) waiting for "domcontentloaded" (fast, reliable) instead of
    "networkidle" for the initial navigation, then an explicit fixed
    pause to give client-side JS time to render, instead of gambling on
    network activity ever going fully quiet.

Politeness: still sleeps between requests; runs on a schedule, not
continuously.
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

RENDER_PAUSE_SECONDS = 3.0  # time given to client-side JS to render after each navigation
NAV_TIMEOUT_MS = 20000      # domcontentloaded is fast — no need for the old 45s allowance


@dataclass
class QAEntry:
    id: str  # e.g. "ls-2026-session1-1234"
    house: str  # "Lok Sabha" | "Rajya Sabha"
    question_number: Optional[str] = None
    question_type: Optional[str] = None  # Starred / Unstarred
    title: str = ""
    member_name: Optional[str] = None
    member_constituency: Optional[str] = None  # e.g. "Kota-Bundi, Rajasthan" — best-effort,
                                                 # see fetch_qa_detail's TODO on where this lives
    ministry: Optional[str] = None
    # The date the question is/was scheduled to be answered — each ministry
    # has fixed weekdays for answering, so this is a real scheduled date,
    # not a rolling deadline. Once this date has passed, we treat the
    # question as due; if answer_text is still empty past that date, the
    # frontend shows "overdue" rather than a countdown. See module
    # docstring for why we're not treating this as a fixed N-day SLA.
    listed_date: Optional[str] = None
    question_text: str = ""
    answer_text: str = ""
    url: Optional[str] = None

    @property
    def is_answered(self) -> bool:
        return bool(self.answer_text.strip())


class SansadSession:
    """Wraps a single reused Playwright browser for the whole scrape run.
    Use as a context manager:

        with SansadSession() as session:
            results = session.search_qa("ls", "solar energy")
            detail = session.fetch_qa_detail(results[0])

    Each call opens/closes a lightweight page, not a whole new browser —
    this is the main fix for the slow first version of this scraper.
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

    def search_qa(self, house: str, keyword: str, max_results: int = 15) -> list[QAEntry]:
        if not self.available:
            return []

        house_label = "Lok Sabha" if house == "ls" else "Rajya Sabha"
        entries: list[QAEntry] = []
        page = self._browser.new_page()
        try:
            page.goto(HOUSES[house], wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            page.wait_for_timeout(int(RENDER_PAUSE_SECONDS * 1000))

            # --- Fill the search form ---
            # TODO: verify these against the real page (see module docstring).
            try:
                page.get_by_label("Search On").select_option(label="Title")
            except Exception:
                logger.debug("Could not set 'Search On' dropdown — using page default")

            try:
                page.get_by_label("Matches On").select_option(label="Any Words")
            except Exception:
                logger.debug("Could not set 'Matches On' dropdown — using page default")

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

            for button_text in ["Apply", "Filter", "Search"]:
                btn = page.get_by_role("button", name=button_text)
                if btn.count() > 0:
                    btn.first.click()
                    break

            # Give the results API call time to resolve — a fixed pause
            # instead of wait_for_load_state("networkidle"), which this
            # kind of app may never satisfy.
            page.wait_for_timeout(int(RENDER_PAUSE_SECONDS * 1000))

            # --- Parse results ---
            # TODO: verify the actual result-row structure.
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
            page.close()

        return entries

    def fetch_qa_detail(self, entry: QAEntry) -> QAEntry:
        """Fetch the full question + answer text, constituency, and
        scheduled answer date for one entry. Best-effort — returns the
        entry with whatever it could find, rather than failing the whole
        run when a locator doesn't match.

        TODO once you've inspected a real detail page: the question/answer
        split below is a text-search heuristic, not a targeted locator,
        because I don't know the actual DOM structure. Replace with direct
        locators for "Question" / "Answer" sections once confirmed.
        """
        if not self.available or not entry.url:
            return entry

        page = self._browser.new_page()
        try:
            page.goto(entry.url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            page.wait_for_timeout(int(RENDER_PAUSE_SECONDS * 1000))
            body_text = page.locator("body").inner_text()

            lower = body_text.lower()
            answer_marker = None
            for marker in ("answer\n", "answer:", "\nanswer"):
                idx = lower.find(marker)
                if idx != -1:
                    answer_marker = idx
                    break
            if answer_marker is not None:
                entry.question_text = body_text[:answer_marker].strip()[:3000]
                entry.answer_text = body_text[answer_marker:].strip()[:3000]
            else:
                entry.question_text = body_text[:3000]
                entry.answer_text = ""

            try:
                constituency_label = page.get_by_text("Constituency", exact=False)
                if constituency_label.count() > 0:
                    entry.member_constituency = constituency_label.first.locator(
                        "xpath=following::text()[1]"
                    ).inner_text().strip()
            except Exception:
                pass

            date_match = re.search(
                r"(?:date of answer|answer date|listed for)\D{0,20}"
                r"([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})",
                body_text, re.IGNORECASE,
            )
            if date_match:
                entry.listed_date = date_match.group(1)
        except Exception:
            logger.exception("Could not fetch Q&A detail for %s", entry.url)
        finally:
            page.close()

        return entry


# Backwards-compatible module-level functions, in case anything still calls
# these directly — each opens its own short-lived session. Prefer
# SansadSession directly (see update_qa.py) for anything that makes more
# than one call, to get the browser-reuse benefit.
def search_qa(house: str, keyword: str, max_results: int = 15) -> list[QAEntry]:
    with SansadSession() as session:
        return session.search_qa(house, keyword, max_results)


def fetch_qa_detail(entry: QAEntry) -> QAEntry:
    with SansadSession() as session:
        return session.fetch_qa_detail(entry)
