# Build Progress

## Status: Active — scrape running via GitHub Actions

---

## Completed

- [x] Step 1: Project skeleton + git repo
- [x] Step 2: Database schema + common data model (`src/db.py`, `src/models.py`)
- [x] Step 3: Empire Flippers scraper (public JSON API, paginated)
- [x] Step 4: SideProjectors scraper (HTML + detail page fetch)
- [x] Step 5: Microns.io scraper (RSS feed + sitemap)
- [x] Step 6: Flippa scraper (JSON API with HTML fallback)
- [x] Step 7: CLI entry point + runner (`main.py`)
- [x] Step 8: Pet & Wellness keyword filter (`src/filters.py`)
  - 60+ keywords covering pets, pet wellness, supplements, mental health, telehealth, etc.
- [x] Step 9: JSON output mode (`--output-file` flag)
- [x] Step 10: GitHub Actions daily scrape workflow (`.github/workflows/scrape.yml`)
  - Runs automatically on push to branch + daily at 01:00 UTC (09:00 CST)
  - Commits results to `data/all_listings.json` and `data/pet_wellness.json`
- [x] Step 11: n8n workflow JSON (`n8n/deal_sourcer_daily.json`)
  - Sequential pipeline: EF → Microns RSS → Flippa → Filter → Feishu
  - Feishu Interactive Card format
  - Runs daily at 01:00 UTC

---

## Data Files (auto-updated by GitHub Actions)

| File | Contents |
|------|----------|
| `data/all_listings.json` | All scraped listings (all sources, no filter) |
| `data/pet_wellness.json` | Pet & Wellness matched listings only |

> First scrape triggered on push of this commit. Results appear after GHA run completes.

---

## n8n Deployment Checklist

1. Import `n8n/deal_sourcer_daily.json` into n8n (Workflows → Import from File)
2. Open **Send to Feishu** node → replace `REPLACE_WITH_YOUR_WEBHOOK_TOKEN`
3. Toggle workflow **Active** for daily automated runs
4. Click **Execute Workflow** for a manual test run

---

## Keyword Coverage (src/filters.py)

**Pet keywords**: pet, dog, cat, puppy, kitten, vet, animal, grooming, pet care,
pet food, pet health, pet insurance, pet tracker, pet training, rabbit, hamster,
aquarium, reptile, 宠物, and 20+ more

**Wellness keywords**: wellness, supplement, nutraceutical, cbd, hemp, meditation,
mindfulness, holistic health, natural health, mental wellness, sleep tracker,
probiotic, gut health, fitness tracker, telehealth, health coaching, yoga app,
健康, and more

---

## Deferred (future sprints)

- Acquire.com scraper (needs account)
- Indie Hackers / Product Hunt integration
- LLM scoring pipeline (relevance + opportunity score)
- Historical trend tracking (price changes over time)
- SideProjectors HTML parser robustness improvements
- Feishu webhook chat ID configuration
