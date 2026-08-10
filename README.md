# CEEW Bill Climate-Impact Register

Tracks bills before Indian Parliament (via PRS Legislative Research) and scores
each one for climate-policy relevance against a rubric built around CEEW's own
15 research areas. Part of a larger 3-module site (this is module 1 of 3 —
trending searches/social and parliamentary Q&A are separate, not-yet-built
modules).

## How it works

```
PRS Bill Track  →  scraper/prs_client.py  →  scraper/scorer.py (Claude API)  →  data/bills.db
                                                                                      ↓
                                                              site/data/bills.json (exported)
                                                                                      ↓
                                                                    Next.js static site
```

There is no server running continuously. A **GitHub Actions** scheduled
workflow (`.github/workflows/update-bills.yml`) runs once a day, re-scrapes
anything new or changed, re-scores it with Claude, and commits the updated
database + JSON straight back into the repo. The site rebuilds automatically
on every push if you connect it to Vercel/Netlify. This keeps the whole thing
free and maintainable by a small team — no server to patch, no uptime to
watch.

## One-time setup

1. **Get an Anthropic API key** at [console.anthropic.com](https://console.anthropic.com),
   and add it as a GitHub Actions secret: repo Settings → Secrets and
   variables → Actions → New repository secret → name it
   `ANTHROPIC_API_KEY`.
2. **Deploy the frontend**: connect this repo to
   [Vercel](https://vercel.com/new) (free tier), set the project root to
   `site/`, and it will auto-deploy on every push, including the automated
   daily commits.
3. **First run**: trigger the workflow manually once (repo → Actions →
   "Update bills data" → Run workflow) rather than waiting for the 03:00 UTC
   cron, so you can check the first scrape looks right.

## Running locally

```bash
cd scraper
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python update_bills.py --year 2026 --limit 20   # small test run first
python update_bills.py                          # full run, all years
```

```bash
cd site
npm install
npm run dev   # http://localhost:3000
```

## Known first-run risk: scraper selectors

`prs_client.py`'s HTML parsing was written against the *rendered text* of
PRS's bill pages (fetched via a page-fetch tool), not against a saved copy of
their actual HTML/CSS class names — PRS's site structure wasn't directly
inspectable while writing this. It uses resilient, text-anchored parsing
(e.g. "find the heading that says 'Highlights of the Bill'") rather than
brittle CSS selectors, but you should expect to spend 30–60 minutes on first
run comparing scraped output against a few bill pages in a browser's "view
source" and adjusting `_extract_section_after_heading` / the status-timeline
parsing in `prs_client.py` if something looks off. Bring me the failing bill
URL and what's wrong and I can help fix the selector.

## The scoring rubric

Documented in full in `scraper/scorer.py`'s system prompt. Summary:

| Dimension | Points | What it measures |
|---|---|---|
| Sectoral relevance | 0–30 | Match to CEEW's 15 research areas (`scraper/ceew_taxonomy.py`) — 20 pts for a primary-area match, up to 10 more for secondary areas |
| Mitigation/adaptation substance | 0–25 | Binding standards, targets, or funding vs. rhetorical mention |
| Enforceability | 0–20 | Penalties, named implementing authority vs. non-binding language |
| Scale of impact | 0–15 | National vs. state, sector-wide vs. narrow |
| Novelty | 0–10 | New legislative framework vs. minor amendment |

Every score comes with a plain-language `rationale` and a `confidence` level;
bills flagged `needs_review` (low confidence, or genuinely borderline climate
relevance) are marked with a &#9873; on the site so your team knows which
scores to sanity-check first, rather than trusting every number blindly.

## Correcting a score

Edit `scraper/overrides.json` (see the docstring at the top of
`scraper/overrides.py` for the format) and push. The next workflow run will
apply your override and — importantly — will never let the automated scorer
overwrite it again, until you remove the entry.

## Data licensing

Bill data comes from PRS Legislative Research under a
[CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/), which
requires attribution wherever the data is displayed — this is already wired
into the site footer (`site/app/layout.tsx`). Don't strip that attribution if
you customize the design.

## What's not built yet

- The trending-searches/social module (Google Trends via SerpApi + Reddit +
  YouTube) and the parliamentary Q&A module (sansad.in) are separate builds —
  ask me to start on either next.
- No admin UI for editing scores in-browser — v1 keeps this to the
  hand-edited `overrides.json` file, on the theory that a small team editing
  a JSON file occasionally is simpler to maintain than a login-gated editing
  UI. Happy to build one later if this becomes a bottleneck.
- No de-duplication against bills that get re-introduced across years under
  a near-identical title (e.g. GST Bill amendments appear most years) — each
  is currently tracked and scored independently, matching how PRS itself
  tracks them.
