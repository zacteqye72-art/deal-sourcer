import json
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper


def _is_real_listing_url(url: str) -> bool:
    """Return True only for actual startup listing pages, not newsletter posts."""
    if not url:
        return False
    # Actual listings live at microns.io/startup-listings/
    if "microns.io/startup-listings/" in url or "microns.io/startup-listing/" in url:
        return True
    # Exclude newsletter posts and blog posts
    if "newsletter.microns.io" in url:
        return False
    if "/p/" in url:
        return False
    return False


class MicronsScraper(BaseScraper):
    name = "microns"
    RSS_URL = "https://newsletter.microns.io/feed"
    SITEMAP_URL = "https://microns.io/sitemap.xml"
    BASE_URL = "https://microns.io"

    def scrape(self) -> list[Listing]:
        listings = []
        seen_urls = set()

        # 1. Parse sitemap for listing URLs (most reliable)
        sitemap_listings = self._scrape_sitemap()
        for listing in sitemap_listings:
            if listing.url not in seen_urls:
                listings.append(listing)
                seen_urls.add(listing.url)

        # 2. Parse RSS feed for any listings linked from newsletter posts
        rss_listings = self._scrape_rss()
        for listing in rss_listings:
            if listing.url not in seen_urls:
                listings.append(listing)
                seen_urls.add(listing.url)

        print(f"  [microns] Fetched {len(listings)} listings")
        return listings

    def _scrape_rss(self) -> list[Listing]:
        listings = []
        try:
            resp = self._get(self.RSS_URL)
            root = ET.fromstring(resp.text)
        except Exception as e:
            print(f"  [microns] Error fetching RSS: {e}")
            return listings

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//entry", ns) or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )

        for item in items:
            try:
                title = self._text(item, "title")
                link = self._text(item, "link")
                if not link:
                    link_el = item.find("link")
                    if link_el is not None:
                        link = link_el.get("href", "")
                desc = (
                    self._text(item, "description")
                    or self._text(item, "summary")
                    or ""
                )

                if not title or not link:
                    continue

                # Look for a startup listing URL embedded in the post content
                listing_url = None
                content = (
                    self._text(item, "content:encoded")
                    or self._text(
                        item,
                        "{http://purl.org/rss/1.0/modules/content/}encoded",
                    )
                    or desc
                )
                if content and "microns.io" in content:
                    soup = BeautifulSoup(content, "html.parser")
                    for a in soup.find_all("a", href=True):
                        if _is_real_listing_url(a["href"]):
                            listing_url = a["href"]
                            break

                # Only keep items that link to a real listing
                if not listing_url:
                    continue

                source_id = listing_url.rstrip("/").split("/")[-1] or title[:50]

                listings.append(
                    Listing(
                        source=self.name,
                        source_id=source_id,
                        title=title,
                        url=listing_url,
                        description=BeautifulSoup(desc, "html.parser").get_text()[
                            :500
                        ]
                        if desc
                        else "",
                        raw_data=json.dumps(
                            {"rss_title": title, "rss_link": link}
                        ),
                    )
                )
            except Exception as e:
                print(f"  [microns] Error parsing RSS item: {e}")
                continue

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
        urls = []
        for url_el in root.findall(".//sm:url/sm:loc", ns):
            if url_el.text and _is_real_listing_url(url_el.text):
                urls.append(url_el.text)
        # Also try without namespace
        for url_el in root.findall(".//url/loc"):
            if url_el.text and _is_real_listing_url(url_el.text):
                urls.append(url_el.text)

        urls = list(set(urls))[:100]  # cap at 100 listings
        print(f"  [microns] Found {len(urls)} listing URLs in sitemap")

        for url in urls:
            try:
                listing = self._fetch_listing_page(url)
                if listing:
                    listings.append(listing)
            except Exception as e:
                print(f"  [microns] Error fetching {url}: {e}")
                continue

        return listings

    def _fetch_listing_page(self, url: str) -> Listing | None:
        if not _is_real_listing_url(url):
            return None
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            title_el = soup.find("h1")
            title_text = (
                title_el.get_text(strip=True) if title_el else url.split("/")[-1]
            )

            # Skip pages that look like blog posts (no price, generic titles)
            if not title_text or len(title_text) < 4:
                return None

            # Look for price
            price = None
            for el in soup.find_all(string=lambda t: t and "$" in str(t)):
                p = parse_price(str(el).strip())
                if p and p > 100:
                    price = p
                    break

            # Description from meta or first paragraphs
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
        except Exception:
            return None

    @staticmethod
    def _text(element, tag: str) -> str:
        el = element.find(tag)
        return el.text.strip() if el is not None and el.text else ""
