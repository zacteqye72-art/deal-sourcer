import time
from abc import ABC, abstractmethod

import requests

from src.models import Listing


class BaseScraper(ABC):
    """Base class for all marketplace scrapers."""

    name: str = "base"
    rate_limit_seconds: float = 1.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DealSourcer/0.1 (micro-acquisition research tool)"
        })
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
