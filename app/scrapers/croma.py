"""
Croma product scraper.

Note: Croma is a popular Indian electronics retail chain owned by Tata Group.
This implementation includes proper selectors for their product listings.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability

logger = logging.getLogger(__name__)


class CromaScraper(BaseScraper):
    """Scraper for Croma product search results."""

    @property
    def source_name(self) -> str:
        return "croma"

    @property
    def base_url(self) -> str:
        return "https://www.croma.com"

    def _build_search_url(self, query: str) -> str:
        """Build Croma search URL."""
        encoded_query = quote_plus(query)
        return f"{self.base_url}/search?q={encoded_query}"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search Croma for products.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        products = []
        url = self._build_search_url(query)

        logger.info(f"Searching Croma for: {query}")

        html = await self.fetch(url)
        if not html:
            logger.warning("Failed to fetch Croma search results")
            return products

        soup = self.parse_html(html)

        # Find product cards
        product_cards = soup.select('div.product-item') or soup.select('div.product-tile') or soup.select('[class*="product"]')

        if not product_cards:
            # Fallback selector
            product_cards = soup.select('div.crp-i')

        for card in product_cards[:max_results]:
            try:
                product = self._parse_product_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing Croma product card: {e}")
                continue

        logger.info(f"Found {len(products)} products on Croma")
        return products

    def _parse_product_card(self, card) -> Optional[Product]:
        """Parse a single product card from search results."""

        # Title
        title_elem = card.select_one('h3.product-title') or card.select_one('a.product-title') or card.select_one('div.product-name')
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        # URL
        link_elem = card.select_one('a[href*="/product/"]') or card.select_one('a.product-link')
        url = ""
        if link_elem and link_elem.get('href'):
            url = self.make_absolute_url(link_elem['href'])

        # Price
        price = None
        original_price = None
        currency = "INR"

        price_elem = card.select_one('span.price') or card.select_one('div.price') or card.select_one('span.amount')
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '')
            try:
                price = float(price_text)
            except ValueError:
                pass

        # Original price (strikethrough)
        original_price_elem = card.select_one('span.mrp') or card.select_one('span.strike') or card.select_one('div.mrp')
        if original_price_elem:
            orig_text = original_price_elem.get_text(strip=True).replace('₹', '').replace(',', '')
            try:
                original_price = float(orig_text)
            except ValueError:
                pass

        # Rating
        rating = None
        rating_elem = card.select_one('span.rating') or card.select_one('div.rating-stars')
        if rating_elem:
            rating_text = rating_elem.get('data-rating') or rating_elem.get_text(strip=True)
            try:
                rating = float(rating_text)
            except ValueError:
                pass

        # Rating count
        rating_count = None
        rating_count_elem = card.select_one('span.review-count') or card.select_one('span.rating-count')
        if rating_count_elem:
            rating_count_text = rating_count_elem.get_text(strip=True).replace('(', '').replace(')', '').replace('reviews', '')
            try:
                rating_count = int(rating_count_text)
            except ValueError:
                pass

        # Image
        image_url = None
        img_elem = card.select_one('img.product-image') or card.select_one('img') or card.select_one('picture img')
        if img_elem and img_elem.get('src'):
            image_url = img_elem['src']
        elif img_elem and img_elem.get('data-src'):
            image_url = img_elem['data-src']
        elif img_elem and img_elem.get('data-original'):
            image_url = img_elem['data-original']

        # Availability
        availability = Availability.IN_STOCK
        if card.select_one('span.out-of-stock') or card.select_one('div.out-of-stock') or card.select_one('span.c-out-of-stock'):
            availability = Availability.OUT_OF_STOCK

        # Discount
        discount_percent = None
        discount_elem = card.select_one('span.discount') or card.select_one('div.discount-badge') or card.select_one('span.discount-tag')
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True).replace('%', '').replace('off', '')
            try:
                discount_percent = float(discount_text)
            except ValueError:
                pass

        # SKU
        sku = ""
        if url:
            # Extract product ID from URL
            if '/p/' in url:
                sku = url.split('/p/')[-1].split('?')[0]
            elif '/product/' in url:
                sku = url.split('/product/')[-1].split('?')[0]

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
            sku=sku,
            discount_percent=discount_percent
        )

        # Calculate discount if not set
        if product.discount_percent is None and original_price and price:
            product.calculate_discount()

        return product
