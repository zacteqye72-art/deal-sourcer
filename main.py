#!/usr/bin/env python3
"""Deal Sourcer — micro-acquisition deal sourcing pipeline."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.db import init_db, upsert_listing, get_listings
from src.filters import is_pet_related
from src.scrapers.acquire import AcquireScraper
from src.scrapers.empire_flippers import EmpireFlippersScraper
from src.scrapers.sideprojectors import SideProjectorsScraper
from src.scrapers.microns import MicronsScraper
from src.scrapers.flippa import FlippaScraper

SCRAPERS = {
    "empire_flippers": EmpireFlippersScraper,
    "acquire": AcquireScraper,
    "sideprojectors": SideProjectorsScraper,
    "microns": MicronsScraper,
    "flippa": FlippaScraper,
}


def run_scrapers(scraper_names: list[str]) -> tuple[int, int, int]:
    """Run specified scrapers, store results. Returns (total, new, pet_wellness_count)."""
    total = 0
    new_count = 0
    pet_count = 0

    for name in scraper_names:
        cls = SCRAPERS.get(name)
        if not cls:
            print(f"Unknown scraper: {name}. Available: {', '.join(SCRAPERS)}")
            continue

        print(f"\nScraping {name}...")
        scraper = cls()
        try:
            listings = scraper.scrape()
        except Exception as e:
            print(f"  Error: {e}")
            continue

        for listing in listings:
            listing.is_pet_related = is_pet_related(listing)
            is_new = upsert_listing(listing)
            total += 1
            if is_new:
                new_count += 1
            if listing.is_pet_related:
                pet_count += 1

    return total, new_count, pet_count


def print_summary(new_only: bool, pet_only: bool):
    """Print a summary table of listings from DB."""
    rows = get_listings(new_only=new_only, pet_only=pet_only)

    if not rows:
        label = "pet/wellness " if pet_only else ""
        print(f"\nNo {label}listings found.")
        return

    print(f"\n{'Source':<20} {'Title':<45} {'Price':>12} {'Match?':>6}")
    print("-" * 86)
    for row in rows:
        price_str = f"${row['asking_price']:,.0f}" if row["asking_price"] else "N/A"
        pet_flag = "Yes" if row["is_pet_related"] else ""
        title = row["title"][:43]
        print(f"{row['source']:<20} {title:<45} {price_str:>12} {pet_flag:>6}")

    print(f"\nTotal: {len(rows)} listings")


def write_json_output(rows: list[dict], output_file: str, meta: dict):
    """Write listings as structured JSON to a file."""
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "scraped_at": now,
        "total": meta.get("total", len(rows)),
        "new_count": meta.get("new_count", 0),
        "pet_wellness_count": meta.get("pet_wellness_count", sum(1 for r in rows if r.get("is_pet_related"))),
        "listings": [
            {
                "source": r["source"],
                "source_id": r["source_id"],
                "title": r["title"],
                "url": r["url"],
                "asking_price": r["asking_price"],
                "mrr": r["mrr"],
                "annual_profit": r["annual_profit"],
                "multiple": r["multiple"],
                "monetization_type": r["monetization_type"],
                "platform": r["platform"],
                "description": (r["description"] or "")[:300],
                "is_pet_wellness": bool(r["is_pet_related"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ],
    }
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nJSON written to {output_file} ({len(rows)} listings)")


def main():
    parser = argparse.ArgumentParser(description="Deal Sourcer — micro-acquisition pipeline")
    parser.add_argument("--scraper", type=str, help=f"Run specific scraper: {', '.join(SCRAPERS)}")
    parser.add_argument("--new-only", action="store_true", help="Show only new listings since last run")
    parser.add_argument("--no-pet-filter", action="store_true", help="Show all listings, not just pet/wellness")
    parser.add_argument("--list", action="store_true", help="Only list DB contents, don't scrape")
    parser.add_argument("--output-file", type=str, metavar="PATH",
                        help="Write results as JSON to this file path")
    args = parser.parse_args()

    init_db()

    pet_only = not args.no_pet_filter
    meta: dict = {}

    if not args.list:
        scraper_names = [args.scraper] if args.scraper else list(SCRAPERS.keys())
        total, new_count, pet_count = run_scrapers(scraper_names)
        meta = {"total": total, "new_count": new_count, "pet_wellness_count": pet_count}
        print(f"\n--- Scrape complete: {total} processed, {new_count} new, {pet_count} pet/wellness ---")

    if args.output_file:
        rows = get_listings(new_only=args.new_only, pet_only=pet_only)
        write_json_output(rows, args.output_file, meta)
    else:
        print_summary(new_only=args.new_only, pet_only=pet_only)


if __name__ == "__main__":
    main()
