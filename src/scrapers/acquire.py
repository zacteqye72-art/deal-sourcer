"""Acquire.com (formerly MicroAcquire) scraper.

Uses the public listings API and the sitemap for discovery.
"""
import json

from bs4 import BeautifulSoup

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper


class AcquireScraper(BaseScraper):
    name = "acquire"
    # Try multiple browse URL candidates in order
    BROWSE_URLS = [
        "https://acquire.com/listings",
        "https://acquire.com/",
        "https://acquire.com/search",
    ]
    SITEMAP_URL = "https://acquire.com/sitemap.xml"

    def scrape(self) -> list[Listing]:
        listings = self._scrape_browse()
        if not listings:
            listings = self._scrape_sitemap()
        print(f"  [acquire] Fetched {len(listings)} listings")
        return listings

    def _scrape_browse(self) -> list[Listing]:
        """Try known browse URLs and extract embedded JSON or listing cards."""
        listings = []
        resp = None
        for browse_url in self.BROWSE_URLS:
            try:
                resp = self._get(browse_url)
                print(f"  [acquire] Browse URL ok: {browse_url} (status {resp.status_code})")
                break
            except Exception as e:
                print(f"  [acquire] Browse URL failed: {browse_url}: {e}")
                resp = None
        if resp is None:
            return listings

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for JSON embedded in <script type="application/json"> or __NEXT_DATA__
        for script in soup.find_all("script", {"id": "__NEXT_DATA__"}):
            try:
                data = json.loads(script.string or "")
                listings = self._extract_from_next_data(data)
                if listings:
                    return listings
            except Exception:
                pass

        # Fallback: look for listing cards in HTML
        cards = soup.select(
            "[class*='listing'], [class*='Listing'], "
            "[data-listing-id], article, .card"
        )
        for card in cards:
            link = card.find("a", href=lambda h: h and "/listings/" in h)
            if not link:
                continue
            href = link["href"]
            if not href.startswith("http"):
                href = f"https://acquire.com{href}"

            title_el = card.find(["h2", "h3", "h4", ".title"])
            title = title_el.get_text(strip=True) if title_el else href.split("/")[-1]
            if not title:
                continue

            source_id = href.rstrip("/").split("/")[-1]
            price_text = card.find(string=lambda t: t and "$" in str(t))
            price = parse_price(str(price_text)) if price_text else None

            desc_el = card.find("p")
            desc = desc_el.get_text(strip=True)[:400] if desc_el else ""

            listings.append(Listing(
                source=self.name,
                source_id=source_id,
                title=title,
                url=href,
                asking_price=price,
                description=desc,
                raw_data=json.dumps({"card_url": href}),
            ))

        if not listings:
            print(f"  [acquire] browse page: no cards found (status {resp.status_code})")

        return listings

    def _extract_from_next_data(self, data: dict) -> list[Listing]:
        """Extract listings from Next.js __NEXT_DATA__ JSON."""
        listings = []
        # Walk the props/pageProps tree looking for arrays of listing objects
        queue = [data]
        while queue:
            obj = queue.pop()
            if isinstance(obj, dict):
                for v in obj.values():
                    if isinstance(v, (dict, list)):
                        queue.append(v)
                # Check if this dict looks like a listing
                if obj.get("id") and (obj.get("asking_price") or obj.get("title") or obj.get("name")):
                    listing = self._parse_acquire_item(obj)
                    if listing:
                        listings.append(listing)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        queue.append(item)
        return listings

    def _scrape_sitemap(self) -> list[Listing]:
        """Fall back to sitemap listing URLs. Handles sitemap index files."""
        import xml.etree.ElementTree as ET
        listings = []
        _listing_patterns = ("/listings/", "/listing/", "/startup/", "/saas/", "/app/")
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        def _collect_urls(sitemap_url: str, depth: int = 0) -> set:
            if depth > 2:
                return set()
            try:
                resp = self._get(sitemap_url)
                root = ET.fromstring(resp.text)
            except Exception as e:
                print(f"  [acquire] Sitemap fetch error ({sitemap_url}): {e}")
                return set()

            # Check if this is a sitemap index (has <sitemap> children)
            child_sitemaps = (
                root.findall(".//sm:sitemap/sm:loc", ns)
                or root.findall(".//sitemap/loc")
            )
            if child_sitemaps:
                child_urls = [el.text for el in child_sitemaps if el.text]
                print(f"  [acquire] Sitemap index at {sitemap_url}: {len(child_urls)} child sitemaps")
                result = set()
                for child_url in child_urls[:10]:  # limit child sitemaps
                    result |= _collect_urls(child_url, depth + 1)
                return result

            # Flat sitemap — collect matching URLs
            all_locs = (
                root.findall(".//sm:url/sm:loc", ns)
                or root.findall(".//url/loc")
            )
            sample = [el.text for el in all_locs[:5] if el.text]
            if sample and depth == 0:
                print(f"  [acquire] Sitemap sample URLs: {sample}")
            return {
                el.text for el in all_locs
                if el.text and any(p in el.text for p in _listing_patterns)
            }

        urls = _collect_urls(self.SITEMAP_URL)
        print(f"  [acquire] Found {len(urls)} listing URLs in sitemap")
        for url in sorted(urls)[:80]:
            try:
                listing = self._fetch_listing_page(url)
                if listing:
                    listings.append(listing)
            except Exception as e:
                print(f"  [acquire] Error fetching {url}: {e}")

        return listings

    def _fetch_listing_page(self, url: str) -> Listing | None:
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.find("h1") or soup.find("h2")
            og_title = soup.find("meta", property="og:title")
            title = (
                title_el.get_text(strip=True) if title_el
                else (og_title["content"] if og_title else url.split("/")[-1])
            )
            if not title:
                return None

            price = None
            for el in soup.find_all(string=lambda t: t and "$" in str(t)):
                p = parse_price(str(el))
                if p and p > 100:
                    price = p
                    break

            desc_meta = soup.find("meta", attrs={"name": "description"})
            og_desc = soup.find("meta", property="og:description")
            desc = (
                (desc_meta["content"] if desc_meta else None)
                or (og_desc["content"] if og_desc else None)
                or " ".join(p.get_text(strip=True) for p in soup.find_all("p")[:3])
            )

            return Listing(
                source=self.name,
                source_id=url.rstrip("/").split("/")[-1],
                title=title,
                url=url,
                asking_price=price,
                description=(desc or "")[:500],
                raw_data=json.dumps({"page_url": url}),
            )
        except Exception:
            return None

    def _parse_acquire_item(self, item: dict) -> Listing | None:
        item_id = str(item.get("id") or item.get("slug") or "")
        if not item_id:
            return None
        title = item.get("title") or item.get("name") or f"Acquire #{item_id}"
        price = parse_price(item.get("asking_price") or item.get("price"))
        revenue = parse_price(item.get("annual_revenue") or item.get("revenue"))
        profit = parse_price(item.get("annual_profit") or item.get("net_profit"))
        url = item.get("url") or f"https://acquire.com/listings/{item_id}"
        if not url.startswith("http"):
            url = f"https://acquire.com{url}"
        return Listing(
            source=self.name,
            source_id=item_id,
            title=title,
            url=url,
            asking_price=price,
            annual_profit=revenue or profit,
            multiple=calc_multiple(price, revenue or profit),
            description=(item.get("description") or item.get("summary") or "")[:500],
            raw_data=json.dumps(item),
        )
