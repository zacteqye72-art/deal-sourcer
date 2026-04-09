import json
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper

LISTING_URL_PREFIXES = (
    "https://www.microns.io/startup-listings/",
    "https://microns.io/startup-listings/",
    "https://www.microns.io/startup-listing/",
    "https://microns.io/startup-listing/",
)


def _is_listing_url(url: str) -> bool:
    return bool(url) and any(url.startswith(p) for p in LISTING_URL_PREFIXES)


class MicronsScraper(BaseScraper):
    name = "microns"
    SITEMAP_URL = "https://microns.io/sitemap.xml"

    def scrape(self) -> list[Listing]:
        """Scrape only via sitemap — avoids newsletter noise from RSS."""
        listings = self._scrape_sitemap()
        print(f"  [microns] Fetched {len(listings)} listings")
        return listings

    def _scrape_sitemap(self) -> list[Listing]:
        listings = []
        try:
            resp = self._get(self.SITEMAP_URL)
            root = ET.fromstring(resp.text)
        except Exception as e:
            print(f"  [microns] Error fetching sitemap: {e}")
            return listings

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls: set[str] = set()
        for url_el in root.findall(".//sm:url/sm:loc", ns):
            if url_el.text and _is_listing_url(url_el.text):
                urls.add(url_el.text)
        for url_el in root.findall(".//url/loc"):
            if url_el.text and _is_listing_url(url_el.text):
                urls.add(url_el.text)

        print(f"  [microns] Found {len(urls)} listing URLs in sitemap")
        url_list = sorted(urls)[:150]  # cap at 150

        for url in url_list:
            try:
                listing = self._fetch_listing_page(url)
                if listing:
                    listings.append(listing)
            except Exception as e:
                print(f"  [microns] Error fetching {url}: {e}")
                continue

        return listings

    def _fetch_listing_page(self, url: str) -> Listing | None:
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Title from h1
            title_el = soup.find("h1")
            title_text = (
                title_el.get_text(strip=True) if title_el else url.split("/")[-1]
            )
            if not title_text or len(title_text) < 3:
                return None

            # Skip if the page looks like a blog/newsletter post
            # (listing pages have a buy/offer button or price)
            is_listing = bool(
                soup.find(string=lambda t: t and "$" in str(t))
                or soup.find("button", string=lambda t: t and (
                    "buy" in str(t).lower() or "offer" in str(t).lower()
                    or "acquire" in str(t).lower()
                ))
            )
            if not is_listing:
                # Only skip if description also looks like a blog post
                meta_desc = soup.find("meta", attrs={"name": "description"})
                desc_text = meta_desc["content"] if meta_desc else ""
                if not desc_text or len(desc_text) < 20:
                    return None

            # Price
            price = None
            for el in soup.find_all(string=lambda t: t and "$" in str(t)):
                p = parse_price(str(el).strip())
                if p and p > 100:
                    price = p
                    break

            # Description
            desc_meta = soup.find("meta", attrs={"name": "description"})
            description = desc_meta["content"] if desc_meta else ""
            if not description:
                description = " ".join(
                    p.get_text(strip=True) for p in soup.find_all("p")[:3]
                )

            # Revenue
            annual_revenue = None
            for el in soup.find_all(
                string=lambda t: t and "revenue" in str(t).lower()
            ):
                parent = el.find_parent()
                if parent:
                    rev = parse_price(parent.get_text())
                    if rev:
                        annual_revenue = rev
                        break

            source_id = url.rstrip("/").split("/")[-1]
            return Listing(
                source=self.name,
                source_id=source_id,
                title=title_text,
                url=url,
                asking_price=price,
                annual_profit=annual_revenue,
                multiple=calc_multiple(price, annual_revenue),
                description=description[:500],
                raw_data=json.dumps({"page_url": url}),
            )
        except Exception as e:
            print(f"  [microns] Error parsing {url}: {e}")
            return None
