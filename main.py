#!/usr/bin/env python3
"""Deal Sourcer — micro-acquisition deal sourcing pipeline."""

import argparse
import sys

from src.db import init_db, upsert_listing, get_listings
from src.filters import is_pet_related
from src.scrapers.empire_flippers import EmpireFlippersScraper
from src.scrapers.sideprojectors import SideProjectorsScraper
from src.scrapers.microns import MicronsScraper
from src.scrapers.flippa import FlippaScraper

SCRAPERS = {
    "empire_flippers": EmpireFlippersScraper,
    "sideprojectors": SideProjectorsScraper,
    "microns": MicronsScraper,
    "flippa": FlippaScraper,
}


def run_scrapers(scraper_names: list[str]) -> tuple[int, int, int]:
    """Run specified scrapers, store results. Returns (total, new, pet_count)."""
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
        label = "pet-related " if pet_only else ""
        print(f"\nNo {label}listings found.")
        return

    # Print table
    print(f"\n{'Source':<20} {'Title':<45} {'Price':>12} {'Pet?':>5}")
    print("-" * 85)
    for row in rows:
        price_str = f"${row['asking_price']:,.0f}" if row["asking_price"] else "N/A"
        pet_flag = "Yes" if row["is_pet_related"] else ""
        title = row["title"][:43]
        print(f"{row['source']:<20} {title:<45} {price_str:>12} {pet_flag:>5}")

    print(f"\nTotal: {len(rows)} listings")


def main():
    parser = argparse.ArgumentParser(description="Deal Sourcer — micro-acquisition pipeline")
    parser.add_argument("--scraper", type=str, help=f"Run specific scraper: {', '.join(SCRAPERS)}")
    parser.add_argument("--new-only", action="store_true", help="Show only new listings since last run")
    parser.add_argument("--no-pet-filter", action="store_true", help="Show all listings, not just pet-related")
    parser.add_argument("--list", action="store_true", help="Only list DB contents, don't scrape")
    args = parser.parse_args()

    init_db()

    pet_only = not args.no_pet_filter

    if not args.list:
        scraper_names = [args.scraper] if args.scraper else list(SCRAPERS.keys())
        total, new_count, pet_count = run_scrapers(scraper_names)
        print(f"\n--- Scrape complete: {total} processed, {new_count} new, {pet_count} pet-related ---")

    print_summary(new_only=args.new_only, pet_only=pet_only)


if __name__ == "__main__":
    main()
