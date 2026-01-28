"""
Base scraper class providing common functionality for all scrapers.
"""

import asyncio
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.product import Product
from app.utils.rate_limiter import get_rate_limiter
from app.utils.data_cleaner import DataCleaner
from app.config import config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all product scrapers.

    Provides common functionality like HTTP requests, rate limiting,
    and retry logic. Subclasses must implement the search method.
    """

    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
        """Initialize the scraper."""
        self.rate_limiter = get_rate_limiter()
        self.cleaner = DataCleaner()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this source (e.g., 'amazon', 'ebay')."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for this source."""
        pass

    @property
    def domain(self) -> str:
        """Extract domain from base_url for rate limiting."""
        parsed = urlparse(self.base_url)
        return parsed.netloc

    def get_headers(self) -> Dict[str, str]:
        """Get request headers with rotated user agent."""
        headers = config.scraper.default_headers.copy()
        if config.scraper.rotate_user_agents:
            headers["User-Agent"] = random.choice(self.USER_AGENTS)
        else:
            headers["User-Agent"] = self.USER_AGENTS[0]
        return headers

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(config.scraper.request_timeout),
                follow_redirects=True,
                headers=self.get_headers()
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Fetch a URL with rate limiting and retry logic.

        Args:
            url: URL to fetch
            params: Optional query parameters
            retry_count: Current retry attempt number

        Returns:
            Response text or None if failed
        """
        # Apply rate limiting
        await self.rate_limiter.acquire(self.domain)

        try:
            client = await self.get_client()

            # Refresh headers for each request
            headers = self.get_headers()

            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            return response.text

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            if retry_count < config.scraper.max_retries:
                await asyncio.sleep(config.scraper.retry_delay * (retry_count + 1))
                return await self.fetch(url, params, retry_count + 1)
            return None

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} fetching {url}")
            # Retry on 5xx errors
            if e.response.status_code >= 500 and retry_count < config.scraper.max_retries:
                await asyncio.sleep(config.scraper.retry_delay * (retry_count + 1))
                return await self.fetch(url, params, retry_count + 1)
            return None

        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object."""
        return BeautifulSoup(html, 'html.parser')

    def make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute."""
        if not url:
            return ""
        if url.startswith(('http://', 'https://')):
            return url
        return urljoin(self.base_url, url)

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search for products matching the query.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        pass

    def create_product(self, **kwargs) -> Product:
        """
        Create a Product with source automatically set.

        Applies data cleaning to common fields.
        """
        # Clean common fields
        if 'title' in kwargs:
            kwargs['title'] = self.cleaner.clean_title(kwargs['title']) or "Unknown Product"

        if 'url' in kwargs:
            kwargs['url'] = self.cleaner.clean_url(kwargs['url'], self.base_url) or ""

        if 'image_url' in kwargs and kwargs['image_url']:
            kwargs['image_url'] = self.make_absolute_url(kwargs['image_url'])

        if 'image_urls' in kwargs:
            kwargs['image_urls'] = [
                self.make_absolute_url(url) for url in kwargs['image_urls'] if url
            ]

        # Set source
        kwargs['source'] = self.source_name

        return Product(**kwargs)
