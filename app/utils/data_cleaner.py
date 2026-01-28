"""
Data cleaning and normalization utilities for scraped product data.
"""

import re
import html
from typing import Optional, Tuple
from decimal import Decimal, InvalidOperation


class DataCleaner:
    """
    Utility class for cleaning and normalizing scraped product data.
    """

    # Currency symbols mapping
    CURRENCY_SYMBOLS = {
        "$": "USD",
        "£": "GBP",
        "€": "EUR",
        "¥": "JPY",
        "₹": "INR",
        "CAD": "CAD",
        "AUD": "AUD",
    }

    @staticmethod
    def clean_text(text: Optional[str]) -> Optional[str]:
        """
        Clean and normalize text content.

        - Removes extra whitespace
        - Decodes HTML entities
        - Strips leading/trailing whitespace
        """
        if not text:
            return None

        # Decode HTML entities
        text = html.unescape(text)

        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)

        # Strip and return
        text = text.strip()

        return text if text else None

    @staticmethod
    def clean_title(title: Optional[str], max_length: int = 200) -> Optional[str]:
        """
        Clean product title.

        - Removes promotional text patterns
        - Truncates to max length
        """
        if not title:
            return None

        title = DataCleaner.clean_text(title)
        if not title:
            return None

        # Remove common promotional patterns
        patterns_to_remove = [
            r'\[.*?sponsored.*?\]',
            r'\(.*?ad\)',
            r'#\d+\s*(best\s*seller|bestseller)',
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        title = title.strip()

        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."

        return title

    @classmethod
    def parse_price(cls, price_text: Optional[str]) -> Tuple[Optional[float], str]:
        """
        Parse price from text and extract currency.

        Returns:
            Tuple of (price_value, currency_code)
        """
        if not price_text:
            return None, "USD"

        price_text = price_text.strip()

        # Detect currency
        currency = "USD"
        for symbol, code in cls.CURRENCY_SYMBOLS.items():
            if symbol in price_text:
                currency = code
                break

        # Extract numeric value
        # Handle formats like: $1,234.56 or €1.234,56 or ¥1234
        price_text = re.sub(r'[^\d.,]', '', price_text)

        if not price_text:
            return None, currency

        # Handle European format (1.234,56)
        if ',' in price_text and '.' in price_text:
            if price_text.rfind(',') > price_text.rfind('.'):
                # European format: 1.234,56
                price_text = price_text.replace('.', '').replace(',', '.')
            else:
                # US format: 1,234.56
                price_text = price_text.replace(',', '')
        elif ',' in price_text:
            # Could be 1,234 (thousands) or 1,23 (decimal)
            parts = price_text.split(',')
            if len(parts[-1]) == 2:
                # Likely decimal: 1,23 -> 1.23
                price_text = price_text.replace(',', '.')
            else:
                # Likely thousands: 1,234 -> 1234
                price_text = price_text.replace(',', '')

        try:
            price = float(Decimal(price_text))
            return round(price, 2), currency
        except (InvalidOperation, ValueError):
            return None, currency

    @staticmethod
    def parse_rating(rating_text: Optional[str]) -> Optional[float]:
        """
        Parse rating from text like '4.5 out of 5' or '4.5/5' or '4.5 stars'.
        """
        if not rating_text:
            return None

        rating_text = rating_text.lower().strip()

        # Try to find patterns like "4.5 out of 5" or "4.5/5"
        patterns = [
            r'(\d+\.?\d*)\s*(?:out of|\/)\s*5',
            r'(\d+\.?\d*)\s*stars?',
            r'^(\d+\.?\d*)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, rating_text)
            if match:
                try:
                    rating = float(match.group(1))
                    # Normalize to 0-5 scale
                    if rating > 5:
                        rating = rating / 2  # Some sites use 10-point scale
                    return min(5.0, max(0.0, round(rating, 1)))
                except ValueError:
                    continue

        return None

    @staticmethod
    def parse_count(count_text: Optional[str]) -> Optional[int]:
        """
        Parse count numbers like '1,234 reviews' or '1.2K ratings'.
        """
        if not count_text:
            return None

        count_text = count_text.lower().strip()

        # Handle K/M suffixes
        multipliers = {'k': 1000, 'm': 1000000}

        match = re.search(r'([\d,.]+)\s*([km])?', count_text)
        if match:
            try:
                number_str = match.group(1).replace(',', '')
                number = float(number_str)

                suffix = match.group(2)
                if suffix and suffix in multipliers:
                    number *= multipliers[suffix]

                return int(number)
            except ValueError:
                pass

        return None

    @staticmethod
    def parse_availability(text: Optional[str]) -> Tuple[str, Optional[str]]:
        """
        Parse availability status from text.

        Returns:
            Tuple of (availability_enum_value, original_text)
        """
        from app.models.product import Availability

        if not text:
            return Availability.UNKNOWN.value, None

        text_lower = text.lower().strip()

        # Check for out of stock patterns
        out_of_stock_patterns = [
            'out of stock', 'sold out', 'unavailable',
            'currently unavailable', 'not available'
        ]
        for pattern in out_of_stock_patterns:
            if pattern in text_lower:
                return Availability.OUT_OF_STOCK.value, text

        # Check for in stock patterns
        in_stock_patterns = [
            'in stock', 'available', 'ships from',
            'add to cart', 'buy now', 'in-stock'
        ]
        for pattern in in_stock_patterns:
            if pattern in text_lower:
                return Availability.IN_STOCK.value, text

        # Check for limited availability
        limited_patterns = [
            'only', 'left in stock', 'limited', 'few remaining',
            'low stock', 'almost gone'
        ]
        for pattern in limited_patterns:
            if pattern in text_lower:
                return Availability.LIMITED.value, text

        # Check for pre-order
        preorder_patterns = ['pre-order', 'preorder', 'coming soon']
        for pattern in preorder_patterns:
            if pattern in text_lower:
                return Availability.PRE_ORDER.value, text

        return Availability.UNKNOWN.value, text

    @staticmethod
    def clean_url(url: Optional[str], base_url: str = "") -> Optional[str]:
        """
        Clean and normalize URL.

        - Converts relative URLs to absolute
        - Removes tracking parameters
        """
        if not url:
            return None

        url = url.strip()

        # Handle relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/') and base_url:
            url = base_url.rstrip('/') + url

        # Remove common tracking parameters
        tracking_params = [
            'ref', 'tag', 'utm_source', 'utm_medium', 'utm_campaign',
            'utm_content', 'utm_term', 'fbclid', 'gclid'
        ]

        # Simple parameter removal (not handling all edge cases)
        for param in tracking_params:
            url = re.sub(rf'[?&]{param}=[^&]*', '', url)

        # Clean up any double & or trailing ?
        url = re.sub(r'[?&]+$', '', url)
        url = re.sub(r'\?&', '?', url)
        url = re.sub(r'&&+', '&', url)

        return url

    @staticmethod
    def extract_brand(title: str, known_brands: Optional[list] = None) -> Optional[str]:
        """
        Try to extract brand name from product title.
        """
        if not title:
            return None

        # Common brand extraction: usually the first word or two
        words = title.split()
        if not words:
            return None

        # Check against known brands if provided
        if known_brands:
            title_lower = title.lower()
            for brand in known_brands:
                if brand.lower() in title_lower:
                    return brand

        # Default: return first word if it looks like a brand
        # (capitalized, not a common word)
        first_word = words[0]
        common_words = {'the', 'a', 'an', 'new', 'best', 'top', 'premium'}

        if first_word.lower() not in common_words and len(first_word) > 1:
            return first_word

        return None
