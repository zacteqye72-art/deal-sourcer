import time
from abc import ABC, abstractmethod

import requests

from src.models import Listing

# Neutral research-bot UA — works for sitemaps and public APIs.
# Chrome-style UA was tried and broke EF (empty body) + Microns sitemap (HTML).
_DEFAULT_HEADERS = {
    "User-Agent": "DealSourcer/1.0 (micro-acquisition research; github.com/zacteqye72-art/deal-sourcer)",
    "Accept": "application/json, application/xml, text/xml, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


class BaseScraper(ABC):
    """Base class for all marketplace scrapers."""

    name: str = "base"
    rate_limit_seconds: float = 1.5

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)
        self._last_request_time = 0.0

    def _get(self, url: str, **kwargs) -> requests.Response:
        """Rate-limited GET request."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)

        response = self.session.get(url, timeout=30, **kwargs)
        self._last_request_time = time.time()
        response.raise_for_status()
        return response

    @abstractmethod
    def scrape(self) -> list[Listing]:
        """Scrape the marketplace and return normalized listings."""
        ...
