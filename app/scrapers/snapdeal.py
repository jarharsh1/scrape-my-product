"""
Snapdeal product scraper.

Note: Snapdeal is a popular Indian e-commerce platform.
This implementation includes proper selectors for their product listings.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability

logger = logging.getLogger(__name__)


class SnapdealScraper(BaseScraper):
    """Scraper for Snapdeal product search results."""

    @property
    def source_name(self) -> str:
        return "snapdeal"

    @property
    def base_url(self) -> str:
        return "https://www.snapdeal.com"

    def _build_search_url(self, query: str) -> str:
        """Build Snapdeal search URL."""
        encoded_query = quote_plus(query)
        return f"{self.base_url}/search?q={encoded_query}"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search Snapdeal for products.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        products = []
        url = self._build_search_url(query)

        logger.info(f"Searching Snapdeal for: {query}")

        html = await self.fetch(url)
        if not html:
            logger.warning("Failed to fetch Snapdeal search results")
            return products

        soup = self.parse_html(html)

        # Find product cards
        product_cards = soup.select('div.product-tuple-listing') or soup.select('div.product-card')

        if not product_cards:
            # Fallback selector
            product_cards = soup.select('[class*="product-tuple"]')

        for card in product_cards[:max_results]:
            try:
                product = self._parse_product_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing Snapdeal product card: {e}")
                continue

        logger.info(f"Found {len(products)} products on Snapdeal")
        return products

    def _parse_product_card(self, card) -> Optional[Product]:
        """Parse a single product card from search results."""

        # Title
        title_elem = card.select_one('p.product-title') or card.select_one('a.product-title') or card.select_one('div.product-title')
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        # URL
        link_elem = card.select_one('a.dp-widget-link') or card.select_one('a.product-title') or card.select_one('a[href*="/product/"]')
        url = ""
        if link_elem and link_elem.get('href'):
            url = self.make_absolute_url(link_elem['href'])

        # Price
        price = None
        original_price = None
        currency = "INR"

        price_elem = card.select_one('span.lfloat') or card.select_one('span.product-price') or card.select_one('div.product-price')
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '')
            try:
                price = float(price_text)
            except ValueError:
                pass

        # Original price (strikethrough)
        original_price_elem = card.select_one('span.fright') or card.select_one('span.original-price') or card.select_one('div.original-price')
        if original_price_elem:
            orig_text = original_price_elem.get_text(strip=True).replace('₹', '').replace(',', '')
            try:
                original_price = float(orig_text)
            except ValueError:
                pass

        # Rating
        rating = None
        rating_elem = card.select_one('div.filled') or card.select_one('span.rating-stars')
        if rating_elem:
            # Try to extract rating from stars
            filled_stars = len(card.select('div.filled'))
            rating = float(filled_stars)

        # Image
        image_url = None
        img_elem = card.select_one('img.product-image') or card.select_one('img.lazy-load')
        if img_elem and img_elem.get('src'):
            image_url = img_elem['src']
        elif img_elem and img_elem.get('data-src'):
            image_url = img_elem['data-src']

        # Availability
        availability = Availability.IN_STOCK
        if card.select_one('div.out-of-stock') or card.select_one('span.out-of-stock'):
            availability = Availability.OUT_OF_STOCK

        # Discount
        discount_percent = None
        discount_elem = card.select_one('span.discount-percent') or card.select_one('div.discount-discount')
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True).replace('% off', '').replace('off', '')
            try:
                discount_percent = float(discount_text)
            except ValueError:
                pass

        # SKU
        sku = ""
        if link_elem and link_elem.get('href'):
            href = link_elem.get('href', '')
            # Extract product ID from URL
            if '/product/' in href:
                sku = href.split('/product/')[-1].split('?')[0]

        # Create product
        product = self.create_product(
            title=title,
            url=url,
            price=price,
            original_price=original_price,
            currency=currency,
            availability=availability,
            rating=rating,
            image_url=image_url,
            sku=sku,
            discount_percent=discount_percent
        )

        # Calculate discount if not set
        if product.discount_percent is None and original_price and price:
            product.calculate_discount()

        return product
