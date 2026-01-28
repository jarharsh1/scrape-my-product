"""
Amazon product scraper.

Note: Amazon actively blocks scrapers. This implementation includes
proper selectors but may require proxies or additional measures for
production use.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    """Scraper for Amazon product search results."""

    @property
    def source_name(self) -> str:
        return "amazon"

    @property
    def base_url(self) -> str:
        return "https://www.amazon.com"

    def _build_search_url(self, query: str) -> str:
        """Build Amazon search URL."""
        encoded_query = quote_plus(query)
        return f"{self.base_url}/s?k={encoded_query}"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search Amazon for products.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        products = []
        url = self._build_search_url(query)

        logger.info(f"Searching Amazon for: {query}")

        html = await self.fetch(url)
        if not html:
            logger.warning("Failed to fetch Amazon search results")
            return products

        soup = self.parse_html(html)

        # Find product cards - Amazon uses data-component-type="s-search-result"
        product_cards = soup.select('[data-component-type="s-search-result"]')

        if not product_cards:
            # Fallback selector
            product_cards = soup.select('.s-result-item[data-asin]')

        for card in product_cards[:max_results]:
            try:
                product = self._parse_product_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing Amazon product card: {e}")
                continue

        logger.info(f"Found {len(products)} products on Amazon")
        return products

    def _parse_product_card(self, card) -> Optional[Product]:
        """Parse a single product card from search results."""

        # Skip sponsored/ad products
        if card.select_one('.s-label-popover-default'):
            return None

        # Get ASIN (Amazon's product ID)
        asin = card.get('data-asin', '')
        if not asin:
            return None

        # Title
        title_elem = card.select_one('h2 a span') or card.select_one('.a-text-normal')
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        # URL
        link_elem = card.select_one('h2 a') or card.select_one('a.a-link-normal')
        url = ""
        if link_elem and link_elem.get('href'):
            url = self.make_absolute_url(link_elem['href'])

        # Price - Amazon has complex price structures
        price = None
        original_price = None
        currency = "USD"

        # Current price
        price_whole = card.select_one('.a-price-whole')
        price_fraction = card.select_one('.a-price-fraction')

        if price_whole:
            price_text = price_whole.get_text(strip=True).replace(',', '')
            fraction = price_fraction.get_text(strip=True) if price_fraction else '00'
            try:
                price = float(f"{price_text}.{fraction}")
            except ValueError:
                pass

        # Original price (strikethrough)
        original_price_elem = card.select_one('.a-price.a-text-price .a-offscreen')
        if original_price_elem:
            orig_text = original_price_elem.get_text(strip=True)
            orig_price, _ = self.cleaner.parse_price(orig_text)
            if orig_price:
                original_price = orig_price

        # Rating
        rating = None
        rating_elem = card.select_one('.a-icon-star-small .a-icon-alt, .a-icon-star .a-icon-alt')
        if rating_elem:
            rating = self.cleaner.parse_rating(rating_elem.get_text())

        # Rating count
        rating_count = None
        rating_count_elem = card.select_one('.a-size-small .a-link-normal')
        if rating_count_elem:
            rating_count = self.cleaner.parse_count(rating_count_elem.get_text())

        # Image
        image_url = None
        img_elem = card.select_one('.s-image')
        if img_elem and img_elem.get('src'):
            image_url = img_elem['src']

        # Availability - check for Prime badge or availability text
        availability = Availability.UNKNOWN
        if card.select_one('.a-icon-prime'):
            availability = Availability.IN_STOCK

        # Create product
        product = self.create_product(
            title=title,
            url=url,
            price=price,
            original_price=original_price,
            currency=currency,
            availability=availability,
            rating=rating,
            rating_count=rating_count,
            image_url=image_url,
            sku=asin
        )

        # Calculate discount
        product.calculate_discount()

        return product
