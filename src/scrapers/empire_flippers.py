import json

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper


class EmpireFlippersScraper(BaseScraper):
    name = "empire_flippers"
    API_URL = "https://api.empireflippers.com/api/v1/listings/list"

    def scrape(self) -> list[Listing]:
        listings = []
        page = 1

        while True:
            params = {
                "listing_status": "Active",
                "sort": "-first_listed_at",
                "page": page,
                "page_size": 50,
            }
            try:
                resp = self._get(self.API_URL, params=params)
                data = resp.json()
            except Exception as e:
                print(f"  [empire_flippers] Error fetching page {page}: {e}")
                break

            results = data.get("results") or data.get("data") or []
            if not results:
                break

            for item in results:
                listing_id = str(item.get("listing_number") or item.get("id", ""))
                if not listing_id:
                    continue

                price = parse_price(item.get("listing_price") or item.get("price"))
                annual = parse_price(item.get("annual_net_profit") or item.get("annual_profit"))
                mrr_val = parse_price(item.get("monthly_net_profit") or item.get("mrr"))
                niche = item.get("niche") or item.get("category") or ""
                monetization = item.get("monetization", [])
                if isinstance(monetization, list):
                    monetization = ", ".join(monetization)

                listings.append(Listing(
                    source=self.name,
                    source_id=listing_id,
                    title=item.get("site_title") or item.get("title") or f"EF #{listing_id}",
                    url=f"https://empireflippers.com/listing/{listing_id}",
                    asking_price=price,
                    mrr=mrr_val,
                    annual_profit=annual,
                    multiple=calc_multiple(price, annual),
                    monetization_type=monetization or None,
                    platform=niche or None,
                    business_age_months=item.get("months_old"),
                    description=item.get("listing_summary") or item.get("summary") or "",
                    raw_data=json.dumps(item),
                ))

            # Check for pagination
            next_url = data.get("next")
            if not next_url:
                break
            page += 1
            if page > 20:  # safety cap
                break

        print(f"  [empire_flippers] Fetched {len(listings)} listings")
        return listings
