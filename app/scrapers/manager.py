"""
Scraper manager for orchestrating multiple scrapers concurrently.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Type
from dataclasses import dataclass, field

from app.scrapers.base import BaseScraper
from app.scrapers.amazon import AmazonScraper
from app.scrapers.ebay import EbayScraper
from app.scrapers.bestbuy import BestBuyScraper
from app.scrapers.flipkart import FlipkartScraper
from app.scrapers.snapdeal import SnapdealScraper
from app.scrapers.reliancedigital import RelianceDigitalScraper
from app.scrapers.croma import CromaScraper
from app.scrapers.tatacliq import TataCliqScraper
from app.scrapers.demo import (
    DemoAmazonScraper,
    DemoEbayScraper,
    DemoBestBuyScraper,
    DemoWalmartScraper,
    DemoFlipkartScraper,
    DemoSnapdealScraper,
    DemoRelianceDigitalScraper,
    DemoCromaScraper,
    DemoTataCliqScraper
)
from app.models.product import Product, ProductSearchResult
from app.config import config

logger = logging.getLogger(__name__)


@dataclass
class ScraperRegistry:
    """Registry of available scrapers."""

    # Real scrapers that hit actual websites
    real_scrapers: Dict[str, Type[BaseScraper]] = field(default_factory=lambda: {
        "amazon": AmazonScraper,
        "ebay": EbayScraper,
        "bestbuy": BestBuyScraper,
        # Indian e-commerce scrapers
        "flipkart": FlipkartScraper,
        "snapdeal": SnapdealScraper,
        "reliancedigital": RelianceDigitalScraper,
        "croma": CromaScraper,
        "tatacliq": TataCliqScraper,
    })

    # Demo scrapers for testing
    demo_scrapers: Dict[str, Type[BaseScraper]] = field(default_factory=lambda: {
        "amazon": DemoAmazonScraper,
        "ebay": DemoEbayScraper,
        "bestbuy": DemoBestBuyScraper,
        "walmart": DemoWalmartScraper,
        # Indian e-commerce demo scrapers
        "flipkart": DemoFlipkartScraper,
        "snapdeal": DemoSnapdealScraper,
        "reliancedigital": DemoRelianceDigitalScraper,
        "croma": DemoCromaScraper,
        "tatacliq": DemoTataCliqScraper,
    })


class ScraperManager:
    """
    Manager for orchestrating multiple product scrapers.

    Handles:
    - Concurrent scraping from multiple sources
    - Error isolation (one scraper failing doesn't affect others)
    - Result aggregation and deduplication
    - Caching (optional)
    """

    def __init__(self, use_demo_scrapers: bool = False):
        """
        Initialize the scraper manager.

        Args:
            use_demo_scrapers: If True, use demo scrapers instead of real ones.
                             Set to False to scrape real websites.
        """
        self.registry = ScraperRegistry()
        self.use_demo_scrapers = use_demo_scrapers
        self._scrapers: Dict[str, BaseScraper] = {}
        self._cache: Dict[str, ProductSearchResult] = {}

    def get_available_sources(self) -> List[str]:
        """Get list of available scraper sources."""
        if self.use_demo_scrapers:
            return list(self.registry.demo_scrapers.keys())
        return list(self.registry.real_scrapers.keys())

    def _get_scraper(self, source: str) -> Optional[BaseScraper]:
        """Get or create a scraper instance for a source."""
        if source not in self._scrapers:
            scrapers = (
                self.registry.demo_scrapers
                if self.use_demo_scrapers
                else self.registry.real_scrapers
            )

            if source not in scrapers:
                return None

            self._scrapers[source] = scrapers[source]()

        return self._scrapers[source]

    async def _scrape_source(
        self,
        source: str,
        query: str,
        max_results: int
    ) -> tuple[str, List[Product], Optional[str]]:
        """
        Scrape a single source and return results.

        Returns:
            Tuple of (source_name, products, error_message)
        """
        scraper = self._get_scraper(source)
        if not scraper:
            return (source, [], f"Unknown source: {source}")

        try:
            products = await scraper.search(query, max_results)
            return (source, products, None)
        except Exception as e:
            logger.error(f"Error scraping {source}: {str(e)}")
            return (source, [], str(e))

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        max_results_per_source: int = 10
    ) -> ProductSearchResult:
        """
        Search for products across multiple sources concurrently.

        Args:
            query: Search term
            sources: List of sources to search (None = all available)
            max_results_per_source: Maximum results per source

        Returns:
            ProductSearchResult containing all found products
        """
        start_time = time.time()

        # Determine which sources to search
        if sources is None:
            sources = self.get_available_sources()
        else:
            # Validate requested sources
            available = set(self.get_available_sources())
            sources = [s for s in sources if s in available]

        if not sources:
            return ProductSearchResult(
                query=query,
                total_results=0,
                products=[],
                sources_searched=[],
                search_time_seconds=0,
                errors={"general": "No valid sources specified"}
            )

        # Check cache
        cache_key = f"{query}:{','.join(sorted(sources))}:{max_results_per_source}"
        if config.enable_caching and cache_key in self._cache:
            cached = self._cache[cache_key]
            # Simple TTL check (could be improved)
            logger.info(f"Returning cached results for: {query}")
            return cached

        # Scrape all sources concurrently
        logger.info(f"Searching {len(sources)} sources for: {query}")

        tasks = [
            self._scrape_source(source, query, max_results_per_source)
            for source in sources
        ]

        results = await asyncio.gather(*tasks)

        # Aggregate results
        all_products: List[Product] = []
        errors: Dict[str, str] = {}
        searched_sources: List[str] = []

        for source, products, error in results:
            searched_sources.append(source)
            if error:
                errors[source] = error
            else:
                all_products.extend(products)

        # Sort by relevance (could be improved with better scoring)
        # For now, prioritize: has rating > has price > alphabetical
        all_products.sort(key=lambda p: (
            p.rating is not None,
            p.price is not None,
            p.title.lower()
        ), reverse=True)

        search_time = time.time() - start_time

        result = ProductSearchResult(
            query=query,
            total_results=len(all_products),
            products=all_products,
            sources_searched=searched_sources,
            search_time_seconds=search_time,
            errors=errors
        )

        # Cache results
        if config.enable_caching:
            self._cache[cache_key] = result

        logger.info(
            f"Search completed: {len(all_products)} products from "
            f"{len(searched_sources)} sources in {search_time:.2f}s"
        )

        return result

    async def close(self):
        """Close all scraper connections."""
        for scraper in self._scrapers.values():
            await scraper.close()
        self._scrapers.clear()

    def clear_cache(self):
        """Clear the result cache."""
        self._cache.clear()


# Global manager instance
_manager: Optional[ScraperManager] = None


def get_scraper_manager(use_demo: bool = False) -> ScraperManager:
    """Get or create the global scraper manager instance.
    
    Args:
        use_demo: Set True to use demo scrapers, False for real scrapers.
    """
    global _manager
    if _manager is None:
        _manager = ScraperManager(use_demo_scrapers=use_demo)
    return _manager


async def shutdown_manager():
    """Shutdown the global scraper manager."""
    global _manager
    if _manager:
        await _manager.close()
        _manager = None
