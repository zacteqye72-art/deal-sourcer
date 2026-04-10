# Build Progress

## Status: Stable — scraping 1,350 listings/run, 113 pet/wellness matches

Last updated: 2026-04-09 (after 10 monitoring/fix rounds)

---

## Completed

- [x] Step 1: Project skeleton + git repo
- [x] Step 2: Database schema + common data model (`src/db.py`, `src/models.py`)
- [x] Step 3: Empire Flippers scraper (public JSON API, paginated)
  - API endpoint: `https://api.empireflippers.com/api/v1/listings/list`
  - Confirmed field names: `public_title`, `average_monthly_net_profit`, `listing_multiple`, `listing_price`, `summary`
  - Recursive `_extract_list()` handles `{data: {listings: [...]}}` JSON:API envelope
  - Full pagination: ~1,000 listings across 20 pages
- [x] Step 4: SideProjectors scraper (HTML — **blocked by GHA IPs, returns 0**)
- [x] Step 5: Microns.io scraper (sitemap-only; RSS removed — caused newsletter noise)
  - Sitemap: 375 listing URLs, cap 150 fetched per run
  - Listing URL prefix: `/startup-listings/`
- [x] Step 6: Flippa scraper (v3 API + HTML fallback — **blocked by GHA IPs, returns 0**)
- [x] Step 7: CLI entry point + runner (`main.py`)
- [x] Step 8: Pet & Wellness keyword filter (`src/filters.py`)
  - 60+ keywords; regex word-boundary matching to prevent false positives
  - "grooming" → "pet grooming" / "dog grooming" to avoid matching beauty listings
- [x] Step 9: JSON output mode (`--output-file` flag)
- [x] Step 10: GitHub Actions daily scrape workflow (`.github/workflows/scrape.yml`)
  - Runs automatically on push to branch + daily at 01:00 UTC (09:00 CST)
  - Commits results to `data/all_listings.json`, `data/pet_wellness.json`, `data/scrape.log`
- [x] Step 11: n8n workflow JSON (`n8n/deal_sourcer_daily.json`)
  - Sequential pipeline: EF → Microns RSS → Flippa → Filter → Feishu Interactive Card
  - Runs daily at 01:00 UTC
- [x] Step 12: Acquire.com scraper (replaces Flippa/SideProjectors which are IP-blocked)
  - Tries browse URLs in order: `/listings` → `/` → `/search`
  - Sitemap index support: follows child sitemaps, handles `.gz` compressed sitemaps
  - 1,320 listing URLs found; 200 fetched per run
  - URL pattern: `https://app.acquire.com/startup/...`

---

## Current Scrape Results (as of 2026-04-09)

| Source | Listings | Pet/Wellness | Notes |
|--------|----------|-------------|-------|
| Empire Flippers | 1,000 | ~99 | Full API pagination working |
| Acquire.com | 200 | ~13 | Sitemap index + gzip |
| Microns.io | 150 | ~1 | Sitemap-only |
| Flippa | 0 | 0 | 403 (GHA IP blocked) |
| SideProjectors | 0 | 0 | 403 (GHA IP blocked) |
| **Total** | **1,350** | **113** | |

---

## Data Files (auto-updated by GitHub Actions)

| File | Contents |
|------|----------|
| `data/all_listings.json` | All 1,350 listings (no filter) |
| `data/pet_wellness.json` | 113 pet & wellness matched listings |
| `data/scrape.log` | Full log output for debugging |

---

## n8n Deployment Checklist

1. Import `n8n/deal_sourcer_daily.json` into n8n (Workflows → Import from File)
2. Open **Send to Feishu** node → replace `REPLACE_WITH_YOUR_WEBHOOK_TOKEN`
3. Toggle workflow **Active** for daily automated runs
4. Click **Execute Workflow** for a manual test run

---

## Keyword Coverage (src/filters.py)

**Pet keywords**: pet, dog, cat, puppy, kitten, vet, animal, pet grooming, dog grooming,
pet care, pet food, pet health, pet insurance, pet tracker, pet training, rabbit, hamster,
aquarium, reptile, 宠物, and more

**Wellness keywords**: wellness, supplement, nutraceutical, cbd, hemp, meditation,
mindfulness, holistic health, natural health, mental wellness, sleep tracker,
probiotic, gut health, fitness tracker, telehealth, health coaching, yoga app,
健康, and more

---

## Known Limitations

- **Flippa** and **SideProjectors** are permanently 403-blocked from GitHub Actions IPs
  — would need a proxy/residential IP to access
- **Acquire.com homepage** renders listings client-side (SPA) — sitemap route is used instead
- EF pagination caps at 20 pages × 50 = 1,000 listings (covers all active listings)
- Microns capped at 150/375 sitemap URLs per run (rate-limited at 1.5s/request)
- Acquire capped at 200/1,320 sitemap URLs per run

---

## Deferred (future sprints)

- Indie Hackers / Product Hunt integration
- LLM relevance scoring (opportunity score 0-100)
- Historical trend tracking (price changes over time)
- Feishu webhook chat ID configuration
- Proxy support for Flippa/SideProjectors access
- Acquire.com full coverage (currently 200/1,320 sitemap URLs)
