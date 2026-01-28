"""
Best Buy product scraper.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability

logger = logging.getLogger(__name__)


class BestBuyScraper(BaseScraper):
    """Scraper for Best Buy product search results."""

    @property
    def source_name(self) -> str:
        return "bestbuy"

    @property
    def base_url(self) -> str:
        return "https://www.bestbuy.com"

    def _build_search_url(self, query: str) -> str:
        """Build Best Buy search URL."""
        encoded_query = quote_plus(query)
        return f"{self.base_url}/site/searchpage.jsp?st={encoded_query}"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search Best Buy for products.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        products = []
        url = self._build_search_url(query)

        logger.info(f"Searching Best Buy for: {query}")

        html = await self.fetch(url)
        if not html:
            logger.warning("Failed to fetch Best Buy search results")
            return products

        soup = self.parse_html(html)

        # Find product cards - Best Buy uses sku-item class
        product_cards = soup.select('.sku-item')

        if not product_cards:
            # Fallback selector
            product_cards = soup.select('[data-sku-id]')

        for card in product_cards[:max_results]:
            try:
                product = self._parse_product_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing Best Buy product card: {e}")
                continue

        logger.info(f"Found {len(products)} products on Best Buy")
        return products

    def _parse_product_card(self, card) -> Optional[Product]:
        """Parse a single product card from search results."""

        # SKU
        sku = card.get('data-sku-id', '')

        # Title
        title_elem = card.select_one('.sku-title a, .sku-header a')
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        # URL
        url = ""
        if title_elem and title_elem.get('href'):
            url = self.make_absolute_url(title_elem['href'])

        # Price
        price = None
        original_price = None
        currency = "USD"

        # Current price
        price_elem = card.select_one('.priceView-customer-price span, .priceView-hero-price span')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price, currency = self.cleaner.parse_price(price_text)

        # Was price (original)
        was_price_elem = card.select_one('.pricing-price__regular-price')
        if was_price_elem:
            was_text = was_price_elem.get_text(strip=True)
            original_price, _ = self.cleaner.parse_price(was_text)

        # Savings/Discount
        discount_percent = None
        savings_elem = card.select_one('.pricing-price__savings')
        if savings_elem:
            savings_text = savings_elem.get_text(strip=True)
            import re
            match = re.search(r'(\d+)%', savings_text)
            if match:
                discount_percent = float(match.group(1))

        # Rating
        rating = None
        rating_elem = card.select_one('.c-ratings-reviews .c-ratings-reviews-v4')
        if rating_elem:
            rating_text = rating_elem.get('aria-label', '')
            rating = self.cleaner.parse_rating(rating_text)

        # Review count
        review_count = None
        review_elem = card.select_one('.c-ratings-reviews-count')
        if review_elem:
            review_count = self.cleaner.parse_count(review_elem.get_text())

        # Image
        image_url = None
        img_elem = card.select_one('.product-image img')
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src')

        # Availability
        availability = Availability.UNKNOWN
        add_to_cart_btn = card.select_one('.add-to-cart-button')
        if add_to_cart_btn:
            btn_text = add_to_cart_btn.get_text(strip=True).lower()
            if 'add to cart' in btn_text:
                availability = Availability.IN_STOCK
            elif 'sold out' in btn_text:
                availability = Availability.OUT_OF_STOCK
            elif 'coming soon' in btn_text:
                availability = Availability.PRE_ORDER

        # Model number
        model = None
        model_elem = card.select_one('.sku-model .sku-value')
        if model_elem:
            model = model_elem.get_text(strip=True)

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
            sku=sku,
            model=model
        )

        return product
