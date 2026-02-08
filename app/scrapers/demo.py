"""
Demo scraper that returns simulated product data.

Useful for development, testing, and demonstrations without
hitting real e-commerce sites.
"""

import asyncio
import random
import hashlib
import base64
from typing import List
from urllib.parse import quote_plus

from app.scrapers.base import BaseScraper
from app.models.product import Product, Availability


class DemoScraper(BaseScraper):
    """
    Demo scraper that generates realistic product data based on search queries.

    This scraper simulates responses from various e-commerce sites,
    allowing the application to be tested without making real HTTP requests.
    """

    # Sample product templates by category - Indian brands and realistic INR prices
    PRODUCT_TEMPLATES = {
        "smartphone": [
            {"brand": "Xiaomi", "prefix": "Redmi Note", "base_price": 12999},
            {"brand": "Xiaomi", "prefix": "Poco", "base_price": 15999},
            {"brand": "Samsung", "prefix": "Galaxy", "base_price": 24999},
            {"brand": "Samsung", "prefix": "Galaxy M", "base_price": 17999},
            {"brand": "Samsung", "prefix": "Galaxy F", "base_price": 16999},
            {"brand": "OnePlus", "prefix": "Nord", "base_price": 27999},
            {"brand": "OnePlus", "prefix": "OnePlus", "base_price": 49999},
            {"brand": "Realme", "prefix": "Narzo", "base_price": 11999},
            {"brand": "Realme", "prefix": "Realme", "base_price": 14999},
            {"brand": "Vivo", "prefix": "Vivo", "base_price": 15999},
            {"brand": "OPPO", "prefix": "OPPO", "base_price": 17999},
            {"brand": "Motorola", "prefix": "Moto", "base_price": 13999},
            {"brand": "Nokia", "prefix": "Nokia", "base_price": 10999},
            {"brand": "Tecno", "prefix": "Camon", "base_price": 12999},
            {"brand": "Infinix", "prefix": "Hot", "base_price": 9999},
        ],
        "laptop": [
            {"brand": "HP", "prefix": "Pavilion", "base_price": 54999},
            {"brand": "HP", "prefix": "OMEN", "base_price": 89999},
            {"brand": "HP", "prefix": "Victus", "base_price": 64999},
            {"brand": "Dell", "prefix": "Inspiron", "base_price": 49999},
            {"brand": "Dell", "prefix": "XPS", "base_price": 129999},
            {"brand": "Dell", "prefix": "G15", "base_price": 74999},
            {"brand": "Lenovo", "prefix": "IdeaPad", "base_price": 44999},
            {"brand": "Lenovo", "prefix": "ThinkPad", "base_price": 79999},
            {"brand": "Lenovo", "prefix": "Legion", "base_price": 94999},
            {"brand": "ASUS", "prefix": "VivoBook", "base_price": 42999},
            {"brand": "ASUS", "prefix": "ROG", "base_price": 119999},
            {"brand": "ASUS", "prefix": "TUF", "base_price": 69999},
            {"brand": "Acer", "prefix": "Aspire", "base_price": 39999},
            {"brand": "Acer", "prefix": "Nitro", "base_price": 64999},
            {"brand": "Apple", "prefix": "MacBook Air", "base_price": 99999},
            {"brand": "Apple", "prefix": "MacBook Pro", "base_price": 149999},
            {"brand": "MSI", "prefix": "GF63", "base_price": 74999},
            {"brand": "Microsoft", "prefix": "Surface", "base_price": 99999},
        ],
        "headphone": [
            {"brand": "boAt", "prefix": "Airdopes", "base_price": 1499},
            {"brand": "boAt", "prefix": "Rockerz", "base_price": 1999},
            {"brand": "boAt", "prefix": "BassHeads", "base_price": 899},
            {"brand": "JBL", "prefix": "Tune", "base_price": 3499},
            {"brand": "JBL", "prefix": "Quantum", "base_price": 5999},
            {"brand": "Sony", "prefix": "WH-1000XM", "base_price": 24999},
            {"brand": "Sony", "prefix": "WI-C", "base_price": 2999},
            {"brand": "Sony", "prefix": "WF-1000XM", "base_price": 19999},
            {"brand": "Noise", "prefix": "Air Buds", "base_price": 1299},
            {"brand": "Noise", "prefix": "Shots", "base_price": 1499},
            {"brand": "Apple", "prefix": "AirPods", "base_price": 14999},
            {"brand": "Apple", "prefix": "AirPods Pro", "base_price": 24999},
            {"brand": "Bose", "prefix": "QuietComfort", "base_price": 29999},
            {"brand": "Skullcandy", "prefix": "Crusher", "base_price": 7999},
            {"brand": "Skullcandy", "prefix": "Hesh", "base_price": 4999},
            {"brand": "PTron", "prefix": "Bassbuds", "base_price": 799},
            {"brand": "Mivi", "prefix": "Duopods", "base_price": 999},
            {"brand": "pTron", "prefix": "Jazz", "base_price": 1499},
        ],
        "tv": [
            {"brand": "Samsung", "prefix": "Crystal", "base_price": 54999},
            {"brand": "Samsung", "prefix": "QLED", "base_price": 129999},
            {"brand": "LG", "prefix": "NanoCell", "base_price": 79999},
            {"brand": "LG", "prefix": "OLED", "base_price": 199999},
            {"brand": "Sony", "prefix": "Bravia", "base_price": 99999},
            {"brand": "OnePlus", "prefix": "Y Series", "base_price": 34999},
            {"brand": "OnePlus", "prefix": "U Series", "base_price": 54999},
            {"brand": "TCL", "prefix": "P-Series", "base_price": 42999},
            {"brand": "Mi", "prefix": "TV 5X", "base_price": 49999},
            {"brand": "Realme", "prefix": "TV", "base_price": 29999},
            {"brand": "Vu", "prefix": "Premium", "base_price": 44999},
            {"brand": "Thomson", "prefix": "9 Series", "base_price": 39999},
            {"brand": "Panasonic", "prefix": "Viera", "base_price": 59999},
            {"brand": "Philips", "prefix": "The One", "base_price": 54999},
        ],
        "tablet": [
            {"brand": "Samsung", "prefix": "Galaxy Tab", "base_price": 29999},
            {"brand": "Samsung", "prefix": "Galaxy Tab A", "base_price": 19999},
            {"brand": "Apple", "prefix": "iPad", "base_price": 44999},
            {"brand": "Apple", "prefix": "iPad Air", "base_price": 64999},
            {"brand": "Apple", "prefix": "iPad Pro", "base_price": 99999},
            {"brand": "Xiaomi", "prefix": "Pad", "base_price": 24999},
            {"brand": "Realme", "prefix": "Pad", "base_price": 13999},
            {"brand": "Lenovo", "prefix": "Tab", "base_price": 12999},
            {"brand": "Lenovo", "prefix": "Tab M", "base_price": 15999},
            {"brand": "Nokia", "prefix": "T21", "base_price": 18999},
            {"brand": "Honor", "prefix": "Pad X", "base_price": 15999},
        ],
        "camera": [
            {"brand": "Canon", "prefix": "EOS", "base_price": 65999},
            {"brand": "Canon", "prefix": "PowerShot", "base_price": 29999},
            {"brand": "Nikon", "prefix": "D5600", "base_price": 59999},
            {"brand": "Nikon", "prefix": "Z50", "base_price": 85999},
            {"brand": "Sony", "prefix": "Alpha", "base_price": 74999},
            {"brand": "Sony", "prefix": "Cyber-shot", "base_price": 34999},
            {"brand": "Fujifilm", "prefix": "X", "base_price": 69999},
            {"brand": "GoPro", "prefix": "Hero", "base_price": 44999},
            {"brand": "DJI", "prefix": "Osmo", "base_price": 34999},
            {"brand": "Insta360", "prefix": "ONE", "base_price": 39999},
        ],
        "watch": [
            {"brand": "Apple", "prefix": "Watch SE", "base_price": 29999},
            {"brand": "Apple", "prefix": "Series", "base_price": 49999},
            {"brand": "Samsung", "prefix": "Watch", "base_price": 24999},
            {"brand": "Noise", "prefix": "Colorfit", "base_price": 1999},
            {"brand": "Noise", "prefix": "Pulse", "base_price": 2499},
            {"brand": "boAt", "prefix": "Wave", "base_price": 2499},
            {"brand": "boAt", "prefix": "Primus", "base_price": 3999},
            {"brand": "Fire-Boltt", "prefix": "Ninja", "base_price": 1599},
            {"brand": "Fire-Boltt", "prefix": "Gladiator", "base_price": 2999},
            {"brand": "Amazfit", "prefix": "Bip", "base_price": 3999},
            {"brand": "Amazfit", "prefix": "GTS", "base_price": 7999},
            {"brand": "Garmin", "prefix": "Venu", "base_price": 44999},
            {"brand": "Fitbit", "prefix": "Sense", "base_price": 39999},
            {"brand": "Titan", "prefix": "Smart", "base_price": 4999},
            {"brand": "Fossil", "prefix": "Gen", "base_price": 24999},
        ],
        "speaker": [
            {"brand": "JBL", "prefix": "Flip", "base_price": 4999},
            {"brand": "JBL", "prefix": "Charge", "base_price": 7999},
            {"brand": "JBL", "prefix": "PartyBox", "base_price": 14999},
            {"brand": "Sony", "prefix": "SRS-XB", "base_price": 5999},
            {"brand": "Sony", "prefix": "LSPX", "base_price": 19999},
            {"brand": "boAt", "prefix": "Stone", "base_price": 1999},
            {"brand": "boAt", "prefix": "Immortal", "base_price": 3499},
            {"brand": "Marshall", "prefix": "Emberton", "base_price": 14999},
            {"brand": "Marshall", "prefix": "Acton", "base_price": 24999},
            {"brand": "Ultimate Ears", "prefix": "Wonderboom", "base_price": 8999},
            {"brand": "Bose", "prefix": "SoundLink", "base_price": 18999},
            {"brand": "Alexa", "prefix": "Echo", "base_price": 4999},
            {"brand": "Google", "prefix": "Nest", "base_price": 7999},
            {"brand": "Zebronics", "prefix": "Bomb", "base_price": 2499},
        ],
        "electronics": [
            {"brand": "Logitech", "prefix": "MX Master", "base_price": 8999},
            {"brand": "Logitech", "prefix": "MK", "base_price": 2999},
            {"brand": "Anker", "prefix": "PowerCore", "base_price": 1999},
            {"brand": "Anker", "prefix": "Soundcore", "base_price": 4999},
            {"brand": "WD", "prefix": "My Passport", "base_price": 4999},
            {"brand": "Seagate", "prefix": "Expansion", "base_price": 4499},
            {"brand": "SanDisk", "prefix": "Ultra", "base_price": 2999},
            {"brand": "Samsung", "prefix": "T7", "base_price": 7999},
            {"brand": "Crucial", "prefix": "BX", "base_price": 3999},
            {"brand": "Corsair", "prefix": "K70", "base_price": 14999},
            {"brand": "Razer", "prefix": "DeathAdder", "base_price": 4999},
            {"brand": "Razer", "prefix": "BlackWidow", "base_price": 9999},
            {"brand": "HyperX", "prefix": "Cloud", "base_price": 7999},
        ],
        "default": [
            {"brand": "ProBrand", "prefix": "Premium", "base_price": 999},
            {"brand": "TechMax", "prefix": "Advanced", "base_price": 1499},
            {"brand": "ValuePlus", "prefix": "Essential", "base_price": 499},
            {"brand": "EliteGear", "prefix": "Professional", "base_price": 1999},
            {"brand": "SmartChoice", "prefix": "Ultra", "base_price": 799},
        ]
    }

    SAMPLE_SPECS = {
        "smartphone": {
            "Display": ["6.5 inch FHD+", "6.7 inch AMOLED", "6.4 inch Super AMOLED", "6.6 inch IPS LCD"],
            "Processor": ["Snapdragon 8 Gen 2", "Dimensity 9200", "Exynos 2380", "A16 Bionic"],
            "RAM": ["6GB", "8GB", "12GB"],
            "Storage": ["128GB", "256GB", "512GB"],
            "Battery": ["5000mAh", "4500mAh", "6000mAh"],
            "Camera": ["48MP", "50MP", "64MP", "108MP"],
        },
        "laptop": {
            "Processor": ["Intel Core i5", "Intel Core i7", "AMD Ryzen 5", "AMD Ryzen 7", "M2"],
            "RAM": ["8GB", "16GB", "32GB"],
            "Storage": ["512GB SSD", "1TB SSD", "256GB SSD"],
            "Display": ["14 inch FHD", "15.6 inch FHD", "16 inch 2K", "13.3 inch OLED"],
            "Graphics": ["Integrated", "RTX 3050", "RTX 3060", "RTX 4050"],
        },
        "headphone": {
            "Type": ["In-Ear", "Over-Ear", "On-Ear", "True Wireless"],
            "Connectivity": ["Bluetooth 5.0", "Bluetooth 5.2", "Bluetooth 5.3"],
            "Battery": ["20 hours", "30 hours", "40 hours", "Up to 100 hours"],
            "Features": ["Active Noise Cancellation", "Water Resistant", "Fast Charging"],
        },
        "tv": {
            "Screen Size": ["43 inch", "50 inch", "55 inch", "65 inch", "75 inch"],
            "Resolution": ["4K UHD", "Full HD", "Ultra HD"],
            "Panel": ["LED", "OLED", "QLED", "NanoCell"],
            "Smart TV": ["Android TV", "Tizen", "webOS", "Google TV"],
        },
        "default": {
            "Connectivity": ["Bluetooth 5.0", "Wi-Fi 6", "USB-C", "Wireless"],
            "Battery Life": ["10 hours", "20 hours", "All-day battery", "40 hours"],
            "Color": ["Black", "White", "Silver", "Space Gray", "Blue"],
            "Warranty": ["1 Year", "2 Years", "Limited Lifetime"],
        }
    }

    # Color palettes for product images
    COLOR_PALETTES = {
        "Xiaomi": "#ff6900",
        "Redmi": "#ff6900",
        "Poco": "#fd1d1d",
        "Samsung": "#1428a0",
        "Galaxy": "#1428a0",
        "OnePlus": "#f50101",
        "OnePlus": "#f50101",
        "Realme": "#f5c518",
        "Vivo": "#007aff",
        "OPPO": "#007755",
        "Motorola": "#7c4dff",
        "Nokia": "#124191",
        "Tecno": "#e61d2b",
        "Infinix": "#ff3d00",
        "Apple": "#555555",
        "iPhone": "#555555",
        "MacBook": "#555555",
        "HP": "#0096d6",
        "Pavilion": "#0096d6",
        "OMEN": "#ff4500",
        "Victus": "#0096d6",
        "Dell": "#007db8",
        "Inspiron": "#007db8",
        "XPS": "#1e1e1e",
        "G15": "#007db8",
        "Lenovo": "#e2231a",
        "IdeaPad": "#e2231a",
        "ThinkPad": "#000000",
        "Legion": "#e2231a",
        "ASUS": "#0056b3",
        "VivoBook": "#0056b3",
        "ROG": "#ff0000",
        "TUF": "#0056b3",
        "Acer": "#83b81a",
        "Aspire": "#83b81a",
        "Nitro": "#83b81a",
        "MSI": "#d3001c",
        "Microsoft": "#00a4ef",
        "Surface": "#00a4ef",
        "boAt": "#fe2a55",
        "Airdopes": "#fe2a55",
        "Rockerz": "#fe2a55",
        "JBL": "#00469b",
        "Tune": "#00469b",
        "Sony": "#ffffff",
        "WH-1000XM": "#000000",
        "Noise": "#6c5ce7",
        "Air Buds": "#6c5ce7",
        "Bose": "#000000",
        "Skullcandy": "#000000",
        "PTron": "#ff6b00",
        "Mivi": "#3f51b5",
        "Fire-Boltt": "#ff5722",
        "Amazfit": "#ffc107",
        "Garmin": "#007cc3",
        "Fitbit": "#00b0b9",
        "Titan": "#c6a868",
        "Fossil": "#000000",
        "LG": "#a60000",
        "NanoCell": "#a60000",
        "OLED": "#a60000",
        "Sony": "#000000",
        "Bravia": "#000000",
        "TCL": "#c41e3a",
        "Mi": "#ff6709",
        "TV 5X": "#ff6709",
        "Vu": "#ff6b00",
        "Thomson": "#e63946",
        "Panasonic": "#e20074",
        "Philips": "#0d5caf",
        "Canon": "#000000",
        "EOS": "#000000",
        "Nikon": "#fdca40",
        "Z50": "#fdca40",
        "Fujifilm": "#000000",
        "X": "#000000",
        "GoPro": "#000000",
        "Hero": "#000000",
        "DJI": "#000000",
        "Insta360": "#000000",
        "Amazon": "#ff9900",
        "Echo": "#000000",
        "Google": "#4285f4",
        "Nest": "#4285f4",
        "Zebronics": "#000000",
        "default": "#2563eb"
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

    def _get_color_for_brand(self, brand: str) -> str:
        """Get color for product image based on brand."""
        for brand_prefix, color in self.COLOR_PALETTES.items():
            if brand.lower().startswith(brand_prefix.lower()):
                return color
        return self.COLOR_PALETTES["default"]

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

        # Determine category based on keywords
        category = "default"
        category_keywords = {
            "smartphone": ['phone', 'mobile', 'smartphone', 'android', 'iphone'],
            "laptop": ['laptop', 'notebook', 'macbook', 'gaming laptop'],
            "headphone": ['headphone', 'headset', 'earbuds', 'airpods', 'earphone'],
            "tv": ['tv', 'television', 'smart tv', 'led tv', 'oled'],
            "tablet": ['tablet', 'ipad', 'pad'],
            "camera": ['camera', 'dslr', 'mirrorless', 'gopro'],
            "watch": ['watch', 'smartwatch', 'fitness tracker', 'band'],
            "speaker": ['speaker', 'bluetooth speaker', 'smart speaker', 'home pod'],
        }

        for cat, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    category = cat
                    break
            if category != "default":
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
            model_suffix = random.choice(["Pro", "Plus", "Max", "Lite", "SE", "Ultra", "", "5G", "LTE"])

            title = f"{template['brand']} {template['prefix']} {variant_num} {model_suffix} - {query.title()}".strip()

            # Pricing with some variation (INR prices)
            base_price = template['base_price']
            price_variation = random.uniform(0.8, 1.3)
            price = round(base_price * price_variation, -2)  # Round to nearest 100

            # Some products have discounts
            original_price = None
            discount_percent = None
            if random.random() > 0.5:
                discount = random.choice([5, 10, 15, 20, 25, 30])
                original_price = round(price / (1 - discount / 100), -2)
                discount_percent = float(discount)

            # Rating
            rating = round(random.uniform(3.5, 5.0), 1)
            rating_count = random.randint(100, 50000)

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

            # Generate unique SKU
            sku = f"{self._source_id.upper()}-{seed[:8].upper()}"

            # URL points to retailer search for the product
            search_query = quote_plus(title)
            url = f"{self.base_url}/s?k={search_query}"

            # Create a simple colored SVG image as data URI
            color = self._get_color_for_brand(template['brand'])
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="{color}" width="200" height="200"/><text fill="white" font-family="Arial,sans-serif" font-size="14" x="20" y="100" font-weight="bold">{template['brand']}</text><text fill="white" font-family="Arial,sans-serif" font-size="12" x="20" y="125">{template['prefix'][:10]}</text></svg>'''
            image_url = f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"

            product = self.create_product(
                title=title,
                url=url,
                price=price,
                original_price=original_price,
                currency="INR",
                discount_percent=discount_percent,
                availability=availability,
                rating=rating,
                rating_count=rating_count,
                review_count=random.randint(20, rating_count),
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


# Indian site demo scrapers
class DemoFlipkartScraper(DemoScraper):
    """Demo scraper simulating Flipkart."""

    def __init__(self):
        super().__init__("flipkart")

    @property
    def base_url(self) -> str:
        return "https://www.flipkart.com"


class DemoSnapdealScraper(DemoScraper):
    """Demo scraper simulating Snapdeal."""

    def __init__(self):
        super().__init__("snapdeal")

    @property
    def base_url(self) -> str:
        return "https://www.snapdeal.com"


class DemoRelianceDigitalScraper(DemoScraper):
    """Demo scraper simulating Reliance Digital."""

    def __init__(self):
        super().__init__("reliancedigital")

    @property
    def base_url(self) -> str:
        return "https://www.reliancedigital.in"


class DemoCromaScraper(DemoScraper):
    """Demo scraper simulating Croma."""

    def __init__(self):
        super().__init__("croma")

    @property
    def base_url(self) -> str:
        return "https://www.croma.com"


class DemoTataCliqScraper(DemoScraper):
    """Demo scraper simulating Tata Cliq."""

    def __init__(self):
        super().__init__("tatacliq")

    @property
    def base_url(self) -> str:
        return "https://www.tatacliq.com"
