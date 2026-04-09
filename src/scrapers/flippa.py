import json

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper

_RESULTS_KEYS = ("data", "listings", "results", "items")


class FlippaScraper(BaseScraper):
    name = "flippa"
    SEARCH_URL = "https://flippa.com/search"
    API_URL = "https://flippa.com/api/v3/listings"

    def scrape(self) -> list[Listing]:
        listings = self._scrape_api()
        if not listings:
            listings = self._scrape_search_json()
        if not listings:
            listings = self._scrape_search_page()
        print(f"  [flippa] Fetched {len(listings)} listings")
        return listings

    def _scrape_api(self) -> list[Listing]:
        """Try Flippa's internal v3 API."""
        listings = []
        page = 1

        while page <= 5:
            params = {
                "filter[status]": "open",
                "filter[property_type]": "established_website,established_app,starter_site,saas",
                "sort_alias": "-created_at",
                "page[number]": page,
                "page[size]": 50,
            }
            try:
                resp = self._get(self.API_URL, params=params)
                if resp.status_code in (401, 403, 404):
                    print(f"  [flippa] API returned {resp.status_code}, skipping")
                    return []
                data = resp.json()
            except Exception as e:
                if page == 1:
                    print(f"  [flippa] v3 API not accessible: {e}")
                return listings

            results = []
            for key in _RESULTS_KEYS:
                candidate = data.get(key)
                if isinstance(candidate, list) and candidate:
                    results = candidate
                    break

            if not results:
                break

            for item in results:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)

            page += 1

        return listings

    def _scrape_search_json(self) -> list[Listing]:
        """Try Flippa's search endpoint with JSON accept header."""
        listings = []
        for page in range(1, 4):
            try:
                resp = self._get(
                    self.SEARCH_URL,
                    params={
                        "search_type": "active",
                        "sort": "most_recent",
                        "page": page,
                    },
                    headers={"Accept": "application/json"},
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
            except Exception:
                break

            results = []
            for key in _RESULTS_KEYS:
                candidate = data.get(key)
                if isinstance(candidate, list) and candidate:
                    results = candidate
                    break
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
                        f"  [flippa] search JSON: no results. "
                        f"keys={list(data.keys())[:8]}"
                    )
                break

            for item in results:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)

        return listings

    def _scrape_search_page(self) -> list[Listing]:
        """Fallback: scrape the HTML search results page."""
        listings = []
        try:
            from bs4 import BeautifulSoup

            resp = self._get(
                self.SEARCH_URL,
                params={"search_type": "active", "sort": "most_recent"},
            )
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple card selectors
            cards = soup.select(
                "[class*='ListingCard'], [class*='listing-card'], "
                ".search-result, [data-listing-id], [data-id]"
            )
            if not cards:
                # Fallback: any link to a /listing/ or /buy/ page
                cards = soup.find_all(
                    "a", href=lambda h: h and ("/listing/" in h or "/buy/" in h)
                )

            for card in cards:
                link_el = card if card.name == "a" else card.find("a", href=True)
                if not link_el:
                    continue

                href = link_el.get("href", "")
                if not href:
                    continue
                if not href.startswith("http"):
                    href = f"https://flippa.com{href}"

                title_el = card.find(["h2", "h3", "h4"])
                title = (
                    title_el.get_text(strip=True)
                    if title_el
                    else link_el.get_text(strip=True)[:80]
                )
                if not title:
                    continue

                source_id = href.rstrip("/").split("/")[-1]
                price = None
                price_el = card.find(string=lambda t: t and "$" in str(t))
                if price_el:
                    price = parse_price(str(price_el))

                listings.append(
                    Listing(
                        source=self.name,
                        source_id=source_id,
                        title=title,
                        url=href,
                        asking_price=price,
                        raw_data=json.dumps({"search_url": href}),
                    )
                )

            print(f"  [flippa] HTML fallback: found {len(cards)} cards")
        except Exception as e:
            print(f"  [flippa] HTML fallback failed: {e}")

        return listings

    def _parse_item(self, item: dict) -> Listing | None:
        """Parse a single Flippa API item dict into a Listing."""
        attrs = item.get("attributes", item)
        listing_id = str(
            item.get("id") or attrs.get("id") or attrs.get("listing_id") or ""
        )
        if not listing_id:
            return None

        title = (
            attrs.get("title")
            or attrs.get("site_name")
            or attrs.get("name")
            or f"Flippa #{listing_id}"
        )
        price = parse_price(
            attrs.get("buy_it_now_price")
            or attrs.get("current_price")
            or attrs.get("price")
            or attrs.get("asking_price")
        )
        revenue = parse_price(
            attrs.get("average_monthly_revenue") or attrs.get("revenue")
        )
        profit = parse_price(
            attrs.get("average_monthly_profit") or attrs.get("profit")
        )
        annual_profit = profit * 12 if profit else None
        mrr = revenue

        url = attrs.get("url") or f"https://flippa.com/listing/{listing_id}"
        if not url.startswith("http"):
            url = f"https://flippa.com{url}"

        return Listing(
            source=self.name,
            source_id=listing_id,
            title=title,
            url=url,
            asking_price=price,
            mrr=mrr,
            annual_profit=annual_profit,
            multiple=calc_multiple(price, annual_profit),
            monetization_type=(
                attrs.get("revenue_sources") or attrs.get("property_type")
            ),
            platform=(attrs.get("property_type") or attrs.get("site_type")),
            description=(attrs.get("summary") or attrs.get("description") or ""),
            raw_data=json.dumps(item),
        )
