import json

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper

# Known top-level response keys, in preference order
_RESULTS_KEYS = ("results", "listings", "data", "items", "response")


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

            # Find the results list — try each known key
            results = []
            for key in _RESULTS_KEYS:
                candidate = data.get(key)
                if isinstance(candidate, list) and candidate:
                    results = candidate
                    break
                # Some APIs wrap inside a nested dict
                if isinstance(candidate, dict):
                    for inner_key in _RESULTS_KEYS:
                        inner = candidate.get(inner_key)
                        if isinstance(inner, list) and inner:
                            results = inner
                            break
                    if results:
                        break

            if not results:
                if page == 1:
                    print(
                        f"  [empire_flippers] No results found. "
                        f"Response keys: {list(data.keys())[:10]}. "
                        f"Status: {resp.status_code}"
                    )
                break

            for item in results:
                listing_id = str(
                    item.get("listing_number")
                    or item.get("id")
                    or item.get("listing_id")
                    or ""
                )
                if not listing_id:
                    continue

                price = parse_price(
                    item.get("listing_price")
                    or item.get("price")
                    or item.get("asking_price")
                )
                annual = parse_price(
                    item.get("annual_net_profit")
                    or item.get("annual_profit")
                    or item.get("net_profit_annualized")
                )
                mrr_val = parse_price(
                    item.get("monthly_net_profit")
                    or item.get("mrr")
                    or item.get("monthly_profit")
                )
                niche = (
                    item.get("niche")
                    or item.get("category")
                    or item.get("industry")
                    or ""
                )
                monetization = item.get("monetization", [])
                if isinstance(monetization, list):
                    monetization = ", ".join(monetization)

                listings.append(
                    Listing(
                        source=self.name,
                        source_id=listing_id,
                        title=(
                            item.get("site_title")
                            or item.get("title")
                            or item.get("name")
                            or f"EF #{listing_id}"
                        ),
                        url=f"https://empireflippers.com/listing/{listing_id}",
                        asking_price=price,
                        mrr=mrr_val,
                        annual_profit=annual,
                        multiple=calc_multiple(price, annual),
                        monetization_type=monetization or None,
                        platform=niche or None,
                        business_age_months=item.get("months_old"),
                        description=(
                            item.get("listing_summary")
                            or item.get("summary")
                            or item.get("description")
                            or ""
                        ),
                        raw_data=json.dumps(item),
                    )
                )

            # Pagination
            next_url = data.get("next") or data.get("next_page")
            has_more = data.get("has_more") or data.get("has_next_page")
            if not next_url and not has_more:
                break
            page += 1
            if page > 20:  # safety cap
                break

        print(f"  [empire_flippers] Fetched {len(listings)} listings")
        return listings
