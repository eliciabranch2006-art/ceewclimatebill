"""
Scraper for PRS Legislative Research's Bill Track (prsindia.org/billtrack).

PRS licenses this data under CC BY 4.0 — see the disclaimer footer on
every bill page. Attribution ("Source: PRS Legislative Research") must
be shown on the site wherever bill data is displayed; the frontend
already does this in site/app/layout.tsx.

IMPORTANT NOTE ON SELECTORS: these were written against the rendered
text content of prsindia.org pages (fetched 2026-07-14), not against a
saved copy of the raw HTML/CSS classes. PRS's site is Drupal-based and
its exact div/class structure may differ from what's guessed here. The
parsing below deliberately favours resilient text-anchored strategies
(e.g. "find the heading whose text is 'Highlights of the Bill', take
the following list items") over brittle CSS selectors, but you should
expect to spend 30-60 minutes on first run comparing scraped output
against a few bill pages in a browser and adjusting selectors in
`_parse_bill_detail`. Flag me the failing bill URL + what looks wrong
and I can help fix the selector quickly.

Politeness: this scraper sleeps between requests and identifies itself
with a descriptive User-Agent. It should run on a schedule (see
.github/workflows/update-bills.yml), not continuously.
"""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://prsindia.org"
LISTING_URL = f"{BASE_URL}/billtrack"

# PRS's own 7 top-level categories. "Infrastructure and Environment" is the
# highest-yield category for climate bills, but climate-relevant bills also
# show up under Finance (green finance/taxation), Agriculture (food systems),
# and Governance (e.g. disaster management) — so by default we scrape all
# categories and let the LLM scorer decide relevance, rather than
# pre-filtering by PRS category and risking false negatives.
CATEGORIES = [
    "all",
    "agriculture-and-rural-development",
    "finance-industry-and-labour",
    "governance-and-strategic-affairs",
    "health-education-and-social-welfare",
    "constitutional-amendments",
    "rules-and-regulations",
    "infrastructure-and-environment",
]

HEADERS = {
    "User-Agent": "CEEW-ClimateTrendsTracker/0.1 (research tool; contact: <set your team email>)"
}

REQUEST_DELAY_SECONDS = 2.0  # be polite; PRS is a small non-profit's site, not a CDN-backed API


@dataclass
class BillSummary:
    id: str  # slug, e.g. "the-forest-conservation-amendment-bill-2023"
    title: str
    prs_url: str
    status: Optional[str] = None


@dataclass
class BillDetail:
    id: str
    title: str
    prs_url: str
    ministry: Optional[str] = None
    prs_category: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    highlights_text: str = ""
    key_issues_text: str = ""
    status_timeline: list = field(default_factory=list)  # [{stage, chamber, date}]
    bill_pdf_url: Optional[str] = None


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _year_from_title(title: str) -> Optional[int]:
    m = re.search(r"\b(19|20)\d{2}\b", title)
    return int(m.group(0)) if m else None


def fetch_bill_listing(year: Optional[int] = None, max_pages: int = 50) -> list[BillSummary]:
    """Fetch bill titles/URLs/status from the 'all' category listing.

    PRS paginates with ?page=N (Drupal-style). We stop when a page returns
    no new bill links, or when max_pages is hit as a safety valve.
    """
    bills: dict[str, BillSummary] = {}
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(max_pages):
        params = {"page": page} if page else {}
        if year:
            params["year"] = year
        resp = session.get(f"{BASE_URL}/billtrack/category/all", params=params, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Bill entries render as an <h3>/<h2> heading with an <a> to the bill,
        # followed by a short status line. We look for links under /billtrack/
        # that aren't the nav/category links.
        found_this_page = 0
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/billtrack/" not in href:
                continue
            if any(href.rstrip("/").endswith(suffix) for suffix in
                   ("/billtrack", "/billtrack/category/all", *CATEGORIES)):
                continue
            slug = _slug_from_url(href)
            if slug in bills or not link.get_text(strip=True):
                continue
            title = link.get_text(strip=True)
            # Status is usually the next sibling text node / next tag's text
            status = None
            sib = link.find_parent().find_next_sibling() if link.find_parent() else None
            if sib:
                status_text = sib.get_text(strip=True)
                if status_text and len(status_text) < 40:
                    status = status_text
            bills[slug] = BillSummary(
                id=slug,
                title=title,
                prs_url=href if href.startswith("http") else f"{BASE_URL}{href}",
                status=status,
            )
            found_this_page += 1

        logger.info("Listing page %d: found %d new bills (total %d)", page, found_this_page, len(bills))
        if found_this_page == 0:
            break
        time.sleep(REQUEST_DELAY_SECONDS)

    return list(bills.values())


def _extract_section_after_heading(soup: BeautifulSoup, heading_text: str) -> str:
    """Find a heading (b/strong/h*) whose text matches heading_text, and
    concatenate the text of list items / paragraphs that follow it, until
    the next heading of similar style is hit."""
    heading = None
    for tag in soup.find_all(["strong", "b", "h2", "h3", "h4"]):
        if heading_text.lower() in tag.get_text(strip=True).lower():
            heading = tag
            break
    if heading is None:
        return ""

    texts = []
    # Walk forward through siblings at the same level as the heading's
    # containing block, collecting <li> and <p> text until we hit another
    # bolded heading-like element.
    container = heading.find_parent()
    node = heading
    while True:
        node = node.find_next(["li", "p", "strong", "b", "h2", "h3", "h4"])
        if node is None:
            break
        if node.name in ("strong", "b", "h2", "h3", "h4") and node is not heading:
            # Reached the next section heading (PRS bolds section titles)
            candidate = node.get_text(strip=True)
            if candidate and candidate[0:1].isupper() and len(candidate) < 60:
                break
        text = node.get_text(strip=True)
        if text:
            texts.append(text)
        if len(texts) > 40:  # safety valve against runaway walks
            break
    return "\n".join(texts)


def fetch_bill_detail(bill: BillSummary) -> BillDetail:
    resp = requests.get(bill.prs_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    detail = BillDetail(
        id=bill.id,
        title=bill.title,
        prs_url=bill.prs_url,
        status=bill.status,
        year=_year_from_title(bill.title),
    )

    # Ministry: text follows the literal label "Ministry:"
    ministry_label = soup.find(string=re.compile(r"^\s*Ministry\s*:?\s*$"))
    if ministry_label:
        nxt = ministry_label.find_next(string=True)
        if nxt:
            detail.ministry = nxt.strip()

    # Breadcrumb before the bill title usually names the PRS category
    breadcrumb = soup.find(class_=re.compile("breadcrumb", re.I))
    if breadcrumb:
        crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
        for c in crumbs:
            if c not in ("Home", "Bills & Acts", "Bills Parliament"):
                detail.prs_category = c

    detail.highlights_text = _extract_section_after_heading(soup, "Highlights of the Bill")
    detail.key_issues_text = _extract_section_after_heading(soup, "Key Issues and Analysis")

    # Bill PDF: first PDF link under a "Bill Text" label, fallback to any
    # PDF link on the page
    pdf_link = soup.find("a", href=re.compile(r"\.pdf$", re.I), string=re.compile("Bill Text", re.I))
    if pdf_link is None:
        pdf_link = soup.find("a", href=re.compile(r"\.pdf$", re.I))
    if pdf_link:
        detail.bill_pdf_url = pdf_link["href"]

    # Status timeline: PRS renders a horizontal stage tracker (Introduced,
    # In Committee, Passed LS, Passed RS, ...) each with a chamber + date.
    # We look for repeating (stage, chamber, date) text triples.
    timeline = []
    stage_words = {"Introduced", "In Committee", "Report", "Passed", "Withdrawn",
                   "Lapsed", "Negatived", "Draft", "Rules"}
    for tag in soup.find_all(string=re.compile(r"|".join(re.escape(s) for s in stage_words))):
        stage_text = tag.strip()
        if stage_text not in stage_words:
            continue
        date_match = tag.find_next(string=re.compile(r"[A-Z][a-z]{2} \d{1,2}, \d{4}"))
        chamber_match = tag.find_next(string=re.compile(r"Lok Sabha|Rajya Sabha|Joint Committee"))
        timeline.append({
            "stage": stage_text,
            "chamber": chamber_match.strip() if chamber_match else None,
            "date": date_match.strip() if date_match else None,
        })
    detail.status_timeline = timeline

    return detail
