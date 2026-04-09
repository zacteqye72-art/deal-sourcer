import time
from abc import ABC, abstractmethod

import requests

from src.models import Listing

# Browser-like headers reduce 403s from bot-detection
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
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
        """Rate-limited GET request with browser-like headers."""
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
