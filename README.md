# Deal Sourcer

Automated micro-acquisition deal sourcing pipeline. Scrapes listing marketplaces, normalizes data into a common schema, and stores results for analysis.

## Sources

### Active
- [x] Empire Flippers (public REST API)
- [x] SideProjectors (HTML scraping)
- [x] Microns.io (RSS + HTML scraping)
- [x] Flippa (internal API)

### Planned
- [ ] Acquire.com (requires Slack integration or buyer account)
- [ ] Reddit (requires OAuth app registration)
- [ ] Twitter/X (requires API credits)
- [ ] Indie Hackers (requires Algolia key extraction)
- [ ] Product Hunt (requires OAuth token)
- [ ] LLM scoring pipeline
- [ ] Notifications (Slack/Telegram/email)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Run all scrapers
python main.py

# Run a specific scraper
python main.py --scraper empire_flippers

# Show only new listings since last run
python main.py --new-only
```

## Architecture

All sources are normalized into a common `Listing` schema before storage:
- `mrr`, `asking_price`, `multiple`, `monetization_type`, `platform`, `business_age_months`

Database: SQLite (MVP) → PostgreSQL (production)
