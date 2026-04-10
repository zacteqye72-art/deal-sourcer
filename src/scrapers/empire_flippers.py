import json

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper

# EF API returns {"data": [...], "errors": [...]} — JSON:API-style
# The listings array can be at various depths; try all known paths.
_RESULTS_KEYS = ("results", "listings", "data", "items", "response")


def _extract_list(obj) -> list:
    """Recursively search obj for the first non-empty list of dicts."""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return obj
    if isinstance(obj, dict):
        # Try known keys first
        for key in _RESULTS_KEYS:
            candidate = obj.get(key)
            if candidate is None:
                continue
            found = _extract_list(candidate)
            if found:
                return found
    return []


class EmpireFlippersScraper(BaseScraper):
    name = "empire_flippers"
    API_URL = "https://api.empireflippers.com/api/v1/listings/list"

    def scrape(self) -> list[Listing]:
        listings = []
        page = 1

        while True:
            params = {
                # API ignores page_size; uses 'limit'. No listing_status filter —
                # passing "Active" returned count=0 (param name/value not accepted).
                "sort": "-first_listed_at",
                "page": page,
                "limit": 50,
            }
            try:
                resp = self._get(self.API_URL, params=params)
                data = resp.json()
            except Exception as e:
                print(f"  [empire_flippers] Error fetching page {page}: {e}")
                break

            results = _extract_list(data)

            if not results:
                if page == 1:
                    # Log full structure for debugging
                    def _summarise(obj, depth=0):
                        indent = "    " * depth
                        if isinstance(obj, dict):
                            for k, v in list(obj.items())[:8]:
                                print(f"  {indent}{k}: {type(v).__name__}", end="")
                                if isinstance(v, list):
                                    print(f" ({len(v)} items)")
                                elif isinstance(v, dict):
                                    print(f" (keys: {list(v.keys())[:5]})")
                                    if depth < 2:
                                        _summarise(v, depth + 1)
                                else:
                                    print(f" = {str(v)[:80]}")
                        elif isinstance(obj, list):
                            print(f"  [{len(obj)} items]")
                            if obj:
                                _summarise(obj[0], depth + 1)

                    print(
                        f"  [empire_flippers] No results. "
                        f"Status: {resp.status_code}. Structure:"
                    )
                    _summarise(data)
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
                # API confirmed keys: average_monthly_net_profit, listing_multiple
                mrr_val = parse_price(
                    item.get("average_monthly_net_profit")
                    or item.get("monthly_net_profit")
                    or item.get("mrr")
                )
                annual = (mrr_val * 12) if mrr_val else parse_price(
                    item.get("annual_net_profit")
                    or item.get("annual_profit")
                )
                # Use API-provided multiple when available
                api_multiple = item.get("listing_multiple")
                multiple = (
                    float(api_multiple) if api_multiple and str(api_multiple).replace(".", "", 1).isdigit()
                    else calc_multiple(price, annual)
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
                            item.get("public_title")
                            or item.get("site_title")
                            or item.get("listing_title")
                            or item.get("title")
                            or item.get("name")
                            or f"EF #{listing_id}"
                        ),
                        url=f"https://empireflippers.com/listing/{listing_id}",
                        asking_price=price,
                        mrr=mrr_val,
                        annual_profit=annual,
                        multiple=multiple,
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

            # Pagination: pages info is in data["data"] (inner dict), not outer
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            total_pages = inner.get("pages", 1)
            current_page = inner.get("page", page)
            if current_page >= total_pages:
                break
            page += 1
            if page > 20:
                break

        print(f"  [empire_flippers] Fetched {len(listings)} listings")
        return listings
