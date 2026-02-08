"""
Flipkart product scraper.

Note: Flipkart uses dynamic content and may require JavaScript rendering.
This implementation includes proper selectors but may require additional
measures like Playwright for full functionality.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability

logger = logging.getLogger(__name__)


class FlipkartScraper(BaseScraper):
    """Scraper for Flipkart product search results."""

    @property
    def source_name(self) -> str:
        return "flipkart"

    @property
    def base_url(self) -> str:
        return "https://www.flipkart.com"

    def _build_search_url(self, query: str) -> str:
        """Build Flipkart search URL."""
        encoded_query = quote_plus(query)
        return f"{self.base_url}/search?q={encoded_query}"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Search Flipkart for products.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        products = []
        url = self._build_search_url(query)

        logger.info(f"Searching Flipkart for: {query}")

        html = await self.fetch(url)
        if not html:
            logger.warning("Failed to fetch Flipkart search results")
            return products

        soup = self.parse_html(html)

        # Find product cards - Flipkart uses various selectors
        product_cards = soup.select('div._1AtVbE') or soup.select('div._2B099j')

        if not product_cards:
            # Fallback selector
            product_cards = soup.select('[data-id]')

        for card in product_cards[:max_results]:
            try:
                product = self._parse_product_card(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing Flipkart product card: {e}")
                continue

        logger.info(f"Found {len(products)} products on Flipkart")
        return products

    def _parse_product_card(self, card) -> Optional[Product]:
        """Parse a single product card from search results."""

        # Title
        title_elem = card.select_one('div._4rR01T') or card.select_one('a.s1Q9rs') or card.select_one('a.VJczBk')
        title = title_elem.get_text(strip=True) if title_elem else None
        if not title:
            return None

        # URL
        link_elem = card.select_one('a._1fQZEK') or card.select_one('a.s1Q9rs') or card.select_one('a.VJczBk')
        url = ""
        if link_elem and link_elem.get('href'):
            url = self.make_absolute_url(link_elem['href'])

        # Price
        price = None
        original_price = None
        currency = "INR"

        price_elem = card.select_one('div._30jeq3._1_WHN1') or card.select_one('div._1kUE2d')
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '')
            try:
                price = float(price_text)
            except ValueError:
                pass

        # Original price (strikethrough)
        original_price_elem = card.select_one('div._3I9vwc') or card.select_one('div._2gcJ1R')
        if original_price_elem:
            orig_text = original_price_elem.get_text(strip=True).replace('₹', '').replace(',', '')
            try:
                original_price = float(orig_text)
            except ValueError:
                pass

        # Rating
        rating = None
        rating_elem = card.select_one('div._3LWZlK')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            try:
                rating = float(rating_text)
            except ValueError:
                pass

        # Rating count
        rating_count = None
        rating_count_elem = card.select_one('span._2_R_DZ') or card.select_one('span.t-ZTKy')
        if rating_count_elem:
            rating_count_text = rating_count_elem.get_text(strip=True).replace('(', '').replace(')', '').replace(',', '')
            try:
                rating_count = int(rating_count_text)
            except ValueError:
                pass

        # Image
        image_url = None
        img_elem = card.select_one('img._396cs4') or card.select_one('img._2TpP3t')
        if img_elem and img_elem.get('src'):
            image_url = img_elem['src']
        elif img_elem and img_elem.get('data-src'):
            image_url = img_elem['data-src']

        # Availability - check for out of stock badge
        availability = Availability.IN_STOCK
        if card.select_one('div._18Y8U3') or card.select_one('div._1-uti6'):
            availability = Availability.OUT_OF_STOCK

        # Discount badge
        discount_percent = None
        discount_elem = card.select_one('div._3Ay6Sb') or card.select_one('span._1kUE2d')
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True).replace('% off', '')
            try:
                discount_percent = float(discount_text)
            except ValueError:
                pass

        # SKU - from data-id attribute
        sku = card.get('data-id', '')

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
