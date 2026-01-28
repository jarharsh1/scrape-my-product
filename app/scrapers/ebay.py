"""
eBay product scraper.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability

logger = logging.getLogger(__name__)


class EbayScraper(BaseScraper):
    """Scraper for eBay product search results."""

    @property
    def source_name(self) -> str:
        return "ebay"

    @property
    def base_url(self) -> str:
        return "https://www.ebay.com"

    def _build_search_url(self, query: str) -> str:
        """Build eBay search URL."""
        encoded_query = quote_plus(query)
        return f"{self.base_url}/sch/i.html?_nkw={encoded_query}"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search eBay for products.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        products = []
        url = self._build_search_url(query)

        logger.info(f"Searching eBay for: {query}")

        html = await self.fetch(url)
        if not html:
            logger.warning("Failed to fetch eBay search results")
            return products

        soup = self.parse_html(html)

        # Find product cards
        product_cards = soup.select('.s-item')

        if not product_cards:
            # Fallback selector
            product_cards = soup.select('[data-view="mi:1686|iid:1"]')

        for card in product_cards[:max_results + 2]:  # Skip first couple which might be ads
            try:
                product = self._parse_product_card(card)
                if product and len(products) < max_results:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing eBay product card: {e}")
                continue

        logger.info(f"Found {len(products)} products on eBay")
        return products

    def _parse_product_card(self, card) -> Optional[Product]:
        """Parse a single product card from search results."""

        # Title
        title_elem = card.select_one('.s-item__title')
        title = title_elem.get_text(strip=True) if title_elem else None

        # Skip "Shop on eBay" placeholder cards
        if not title or title.lower() == "shop on ebay":
            return None

        # URL
        link_elem = card.select_one('.s-item__link')
        url = ""
        if link_elem and link_elem.get('href'):
            url = link_elem['href']
            # Clean eBay URLs
            if '?' in url:
                url = url.split('?')[0]

        # Price
        price = None
        original_price = None
        currency = "USD"

        price_elem = card.select_one('.s-item__price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Handle price ranges like "$10.00 to $20.00"
            if ' to ' in price_text.lower():
                # Take the lower price
                price_text = price_text.split(' to ')[0].strip()

            price, currency = self.cleaner.parse_price(price_text)

        # Original price (strikethrough)
        original_elem = card.select_one('.s-item__original-price')
        if original_elem:
            orig_text = original_elem.get_text(strip=True)
            original_price, _ = self.cleaner.parse_price(orig_text)

        # Discount
        discount_elem = card.select_one('.s-item__discount')
        discount_percent = None
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            # Extract number from text like "15% off"
            import re
            match = re.search(r'(\d+)%', discount_text)
            if match:
                discount_percent = float(match.group(1))

        # Rating - eBay shows seller ratings, not product ratings
        # But some products show item ratings
        rating = None
        rating_elem = card.select_one('.b-starrating__star')
        if rating_elem:
            # eBay uses width percentage for stars
            style = rating_elem.get('style', '')
            import re
            match = re.search(r'width:\s*([\d.]+)%', style)
            if match:
                # Convert percentage to 5-star rating
                rating = round((float(match.group(1)) / 100) * 5, 1)

        # Review count
        review_count = None
        review_elem = card.select_one('.s-item__reviews-count span')
        if review_elem:
            review_count = self.cleaner.parse_count(review_elem.get_text())

        # Image
        image_url = None
        img_elem = card.select_one('.s-item__image-img')
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src')

        # Shipping info (can indicate availability)
        availability = Availability.IN_STOCK  # eBay items are generally available
        shipping_elem = card.select_one('.s-item__shipping')
        if shipping_elem:
            shipping_text = shipping_elem.get_text(strip=True).lower()
            if 'not available' in shipping_text:
                availability = Availability.OUT_OF_STOCK

        # Item condition
        condition = None
        condition_elem = card.select_one('.SECONDARY_INFO')
        if condition_elem:
            condition = condition_elem.get_text(strip=True)

        # Create product
        product = self.create_product(
            title=title,
            url=url,
            price=price,
            original_price=original_price,
            currency=currency,
            discount_percent=discount_percent,
            availability=availability,
            rating=rating,
            review_count=review_count,
            image_url=image_url,
        )

        # Add condition to specifications
        if condition:
            product.specifications['Condition'] = condition

        return product
