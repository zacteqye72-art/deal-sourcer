# Deal Sourcer

Automated micro-acquisition deal sourcing pipeline. Scrapes acquisition marketplaces, normalizes listings, and filters for pet-related app/project opportunities.

## Sources

- Empire Flippers (public API)
- SideProjectors (HTML scraping)
- Microns.io (RSS + sitemap)
- Flippa (search API)

## Usage

```bash
pip install -r requirements.txt

# Scrape all sources
python main.py

# Scrape a specific source
python main.py --scraper empire_flippers

# Show only new listings since last run
python main.py --new-only

# Disable pet filter to see all listings
python main.py --no-pet-filter
```

## Data

Results are stored in `deal_sourcer.db` (SQLite). Each listing is deduplicated by `(source, source_id)`.
