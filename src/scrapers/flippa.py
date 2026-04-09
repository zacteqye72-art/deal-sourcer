import json

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper


class FlippaScraper(BaseScraper):
    name = "flippa"
    SEARCH_URL = "https://flippa.com/search"
    API_URL = "https://flippa.com/api/v3/listings"

    def scrape(self) -> list[Listing]:
        listings = []

        # Try the JSON API first, fall back to search page scraping
        listings = self._scrape_api()
        if not listings:
            listings = self._scrape_search_page()

        print(f"  [flippa] Fetched {len(listings)} listings")
        return listings

    def _scrape_api(self) -> list[Listing]:
        """Try Flippa's internal API."""
        listings = []
        page = 1

        while page <= 5:  # cap pages
            params = {
                "filter[status]": "open",
                "filter[property_type]": "established_website,established_app,starter_site,saas",
                "sort_alias": "-created_at",
                "page[number]": page,
                "page[size]": 50,
            }
            try:
                resp = self._get(self.API_URL, params=params)
                data = resp.json()
            except Exception:
                # API might not be publicly accessible, try alternate
                try:
                    alt_params = {
                        "search_type": "active",
                        "sort": "most_recent",
                        "page": page,
                    }
                    resp = self._get(self.SEARCH_URL, params=alt_params, headers={
                        "Accept": "application/json",
                    })
                    data = resp.json()
                except Exception as e:
                    if page == 1:
                        print(f"  [flippa] API not accessible: {e}")
                    break

            results = data.get("data") or data.get("listings") or data.get("results") or []
            if not results:
                break

            for item in results:
                attrs = item.get("attributes", item)
                listing_id = str(item.get("id") or attrs.get("id", ""))
                if not listing_id:
                    continue

                title = attrs.get("title") or attrs.get("site_name") or f"Flippa #{listing_id}"
                price = parse_price(attrs.get("buy_it_now_price") or attrs.get("current_price") or attrs.get("price"))
                revenue = parse_price(attrs.get("average_monthly_revenue") or attrs.get("revenue"))
                profit = parse_price(attrs.get("average_monthly_profit") or attrs.get("profit"))

                annual_profit = profit * 12 if profit else None
                mrr = revenue

                url = attrs.get("url") or f"https://flippa.com/listing/{listing_id}"
                if not url.startswith("http"):
                    url = f"https://flippa.com{url}"

                listings.append(Listing(
                    source=self.name,
                    source_id=listing_id,
                    title=title,
                    url=url,
                    asking_price=price,
                    mrr=mrr,
                    annual_profit=annual_profit,
                    multiple=calc_multiple(price, annual_profit),
                    monetization_type=attrs.get("revenue_sources") or attrs.get("property_type"),
                    platform=attrs.get("property_type") or attrs.get("site_type"),
                    description=attrs.get("summary") or attrs.get("description") or "",
                    raw_data=json.dumps(item),
                ))

            page += 1

        return listings

    def _scrape_search_page(self) -> list[Listing]:
        """Fallback: scrape the HTML search results page."""
        listings = []
        try:
            from bs4 import BeautifulSoup

            resp = self._get(self.SEARCH_URL, params={
                "search_type": "active",
                "sort": "most_recent",
            })
            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select("[class*='ListingCard'], [class*='listing-card'], .search-result")
            for card in cards:
                link = card.find("a", href=True)
                if not link:
                    continue

                href = link["href"]
                if not href.startswith("http"):
                    href = f"https://flippa.com{href}"

                title_el = card.find(["h2", "h3", "h4"])
                title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)[:80]

                source_id = href.rstrip("/").split("/")[-1]

                # Price
                price = None
                price_el = card.find(string=lambda t: t and "$" in str(t))
                if price_el:
                    price = parse_price(str(price_el))

                listings.append(Listing(
                    source=self.name,
                    source_id=source_id,
                    title=title,
                    url=href,
                    asking_price=price,
                    raw_data=json.dumps({"search_url": href}),
                ))

        except Exception as e:
            print(f"  [flippa] Search page scrape failed: {e}")

        return listings
