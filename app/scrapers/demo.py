"""
Demo scraper that returns simulated product data.

Useful for development, testing, and demonstrations without
hitting real e-commerce sites.
"""

import asyncio
import random
import hashlib
from typing import List
from datetime import datetime

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability


class DemoScraper(BaseScraper):
    """
    Demo scraper that generates realistic product data based on search queries.

    This scraper simulates responses from various e-commerce sites,
    allowing the application to be tested without making real HTTP requests.
    """

    # Sample product templates by category
    PRODUCT_TEMPLATES = {
        "electronics": [
            {"brand": "Samsung", "prefix": "Galaxy", "base_price": 799},
            {"brand": "Apple", "prefix": "iPhone", "base_price": 999},
            {"brand": "Sony", "prefix": "WH-1000XM", "base_price": 349},
            {"brand": "Bose", "prefix": "QuietComfort", "base_price": 329},
            {"brand": "Dell", "prefix": "XPS", "base_price": 1299},
            {"brand": "LG", "prefix": "OLED", "base_price": 1499},
            {"brand": "Logitech", "prefix": "MX Master", "base_price": 99},
            {"brand": "Anker", "prefix": "PowerCore", "base_price": 49},
        ],
        "default": [
            {"brand": "ProBrand", "prefix": "Premium", "base_price": 99},
            {"brand": "TechMax", "prefix": "Advanced", "base_price": 149},
            {"brand": "ValuePlus", "prefix": "Essential", "base_price": 49},
            {"brand": "EliteGear", "prefix": "Professional", "base_price": 199},
            {"brand": "SmartChoice", "prefix": "Ultra", "base_price": 79},
        ]
    }

    SAMPLE_SPECS = {
        "electronics": {
            "Connectivity": ["Bluetooth 5.0", "Wi-Fi 6", "USB-C", "Wireless"],
            "Battery Life": ["10 hours", "20 hours", "All-day battery", "40 hours"],
            "Color": ["Black", "White", "Silver", "Space Gray", "Blue"],
            "Warranty": ["1 Year", "2 Years", "Limited Lifetime"],
        },
        "default": {
            "Material": ["Premium Plastic", "Aluminum", "Stainless Steel", "Wood"],
            "Dimensions": ["10 x 5 x 2 inches", "8 x 4 x 3 inches", "Compact"],
            "Weight": ["0.5 lbs", "1.2 lbs", "2.0 lbs", "Lightweight"],
        }
    }

    def __init__(self, source_id: str = "demo"):
        """Initialize demo scraper with optional source identifier."""
        super().__init__()
        self._source_id = source_id

    @property
    def source_name(self) -> str:
        return self._source_id

    @property
    def base_url(self) -> str:
        return f"https://demo-{self._source_id}.example.com"

    async def search(self, query: str, max_results: int = 10) -> List[Product]:
        """
        Generate demo products based on the search query.

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of Product objects
        """
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.3, 1.0))

        products = []
        query_lower = query.lower()

        # Determine category
        electronics_keywords = ['phone', 'laptop', 'headphone', 'speaker', 'tv',
                               'computer', 'tablet', 'camera', 'watch', 'earbuds',
                               'keyboard', 'mouse', 'monitor', 'charger']

        category = "default"
        for keyword in electronics_keywords:
            if keyword in query_lower:
                category = "electronics"
                break

        templates = self.PRODUCT_TEMPLATES.get(category, self.PRODUCT_TEMPLATES["default"])
        specs_pool = self.SAMPLE_SPECS.get(category, self.SAMPLE_SPECS["default"])

        # Generate products
        for i in range(min(max_results, len(templates) * 2)):
            template = templates[i % len(templates)]

            # Create deterministic but varied product
            seed = hashlib.md5(f"{query}-{i}-{self._source_id}".encode()).hexdigest()
            random.seed(seed)

            # Generate product details
            variant_num = random.randint(1, 20)
            model_suffix = random.choice(["Pro", "Plus", "Max", "Lite", "SE", "Ultra", ""])

            title = f"{template['brand']} {template['prefix']} {variant_num} {model_suffix} - {query.title()}".strip()

            # Pricing with some variation
            base_price = template['base_price']
            price_variation = random.uniform(0.7, 1.5)
            price = round(base_price * price_variation, 2)

            # Some products have discounts
            original_price = None
            discount_percent = None
            if random.random() > 0.6:
                discount = random.choice([10, 15, 20, 25, 30])
                original_price = round(price / (1 - discount / 100), 2)
                discount_percent = float(discount)

            # Rating
            rating = round(random.uniform(3.5, 5.0), 1)
            rating_count = random.randint(50, 10000)

            # Availability
            availability_weights = [
                (Availability.IN_STOCK, 0.7),
                (Availability.LIMITED, 0.15),
                (Availability.OUT_OF_STOCK, 0.1),
                (Availability.PRE_ORDER, 0.05),
            ]
            availability = random.choices(
                [a[0] for a in availability_weights],
                [a[1] for a in availability_weights]
            )[0]

            # Specs
            specifications = {}
            for spec_name, spec_values in specs_pool.items():
                if random.random() > 0.3:
                    specifications[spec_name] = random.choice(spec_values)

            # Generate unique SKU and URL
            sku = f"{self._source_id.upper()}-{seed[:8].upper()}"
            url = f"{self.base_url}/product/{sku.lower()}"

            # Placeholder image
            image_url = f"https://via.placeholder.com/300x300.png?text={template['brand']}"

            product = self.create_product(
                title=title,
                url=url,
                price=price,
                original_price=original_price,
                currency="USD",
                discount_percent=discount_percent,
                availability=availability,
                rating=rating,
                rating_count=rating_count,
                review_count=random.randint(10, rating_count),
                brand=template['brand'],
                sku=sku,
                specifications=specifications,
                image_url=image_url,
            )

            products.append(product)

        # Reset random seed
        random.seed()

        return products


class DemoAmazonScraper(DemoScraper):
    """Demo scraper simulating Amazon."""

    def __init__(self):
        super().__init__("amazon")

    @property
    def base_url(self) -> str:
        return "https://www.amazon.com"


class DemoEbayScraper(DemoScraper):
    """Demo scraper simulating eBay."""

    def __init__(self):
        super().__init__("ebay")

    @property
    def base_url(self) -> str:
        return "https://www.ebay.com"


class DemoBestBuyScraper(DemoScraper):
    """Demo scraper simulating Best Buy."""

    def __init__(self):
        super().__init__("bestbuy")

    @property
    def base_url(self) -> str:
        return "https://www.bestbuy.com"


class DemoWalmartScraper(DemoScraper):
    """Demo scraper simulating Walmart."""

    def __init__(self):
        super().__init__("walmart")

    @property
    def base_url(self) -> str:
        return "https://www.walmart.com"
