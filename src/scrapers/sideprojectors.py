import json

from bs4 import BeautifulSoup

from src.models import Listing
from src.normalize import parse_price, calc_multiple
from src.scrapers.base import BaseScraper


class SideProjectorsScraper(BaseScraper):
    name = "sideprojectors"
    BASE_URL = "https://www.sideprojectors.com"
    LIST_URL = f"{BASE_URL}/project/all"

    def scrape(self) -> list[Listing]:
        listings = []

        try:
            resp = self._get(self.LIST_URL, params={
                "type": "side_project",
                "listing_type": "forsale",
            })
        except Exception as e:
            print(f"  [sideprojectors] Error fetching listing page: {e}")
            return listings

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".project-card, .card, [class*='project'], article")

        if not cards:
            # Fallback: look for any links to /project/ pages
            cards = soup.find_all("a", href=lambda h: h and "/project/" in h)

        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as e:
                print(f"  [sideprojectors] Error parsing card: {e}")
                continue

        print(f"  [sideprojectors] Fetched {len(listings)} listings")
        return listings

    def _parse_card(self, card) -> Listing | None:
        # Extract link
        link = card.get("href") if card.name == "a" else None
        if not link:
            link_tag = card.find("a", href=True)
            if link_tag:
                link = link_tag["href"]
        if not link:
            return None

        if not link.startswith("http"):
            link = self.BASE_URL + link

        # Extract title
        title_tag = card.find(["h2", "h3", "h4", ".title", "strong"])
        title = title_tag.get_text(strip=True) if title_tag else card.get_text(strip=True)[:80]
        if not title:
            return None

        # Try to get detail page for more info
        detail = self._fetch_detail(link)

        source_id = link.rstrip("/").split("/")[-1]

        return Listing(
            source=self.name,
            source_id=source_id,
            title=title,
            url=link,
            asking_price=detail.get("price"),
            description=detail.get("description", ""),
            platform=detail.get("tech_stack"),
            monetization_type=detail.get("monetization"),
            raw_data=json.dumps(detail.get("raw", {})),
        )

    def _fetch_detail(self, url: str) -> dict:
        """Fetch a project detail page for additional info."""
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            info = {"raw": {"url": url}}

            # Look for price
            for el in soup.find_all(string=lambda t: t and "$" in t):
                price = parse_price(el.strip())
                if price and price > 0:
                    info["price"] = price
                    break

            # Description
            desc = soup.find("meta", attrs={"name": "description"})
            if desc:
                info["description"] = desc.get("content", "")
            else:
                p_tags = soup.find_all("p")
                if p_tags:
                    info["description"] = " ".join(
                        p.get_text(strip=True) for p in p_tags[:3]
                    )

            # Tech stack
            tech_section = soup.find(string=lambda t: t and "tech" in t.lower())
            if tech_section:
                parent = tech_section.find_parent()
                if parent:
                    info["tech_stack"] = parent.get_text(strip=True)[:200]

            return info
        except Exception:
            return {}
