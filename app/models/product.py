"""
Product data models for structured product information.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class Availability(str, Enum):
    """Product availability status."""
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED = "limited"
    PRE_ORDER = "pre_order"
    UNKNOWN = "unknown"


@dataclass
class Product:
    """
    Structured product data model.

    Contains all scraped and normalized product information.
    """

    # Core identification
    title: str
    source: str  # e.g., "amazon", "ebay", "bestbuy"
    url: str

    # Pricing information
    price: Optional[float] = None
    original_price: Optional[float] = None
    currency: str = "USD"
    discount_percent: Optional[float] = None

    # Availability
    availability: Availability = Availability.UNKNOWN
    availability_text: Optional[str] = None

    # Ratings and reviews
    rating: Optional[float] = None  # e.g., 4.5 out of 5
    rating_count: Optional[int] = None
    review_count: Optional[int] = None

    # Product details
    description: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    sku: Optional[str] = None

    # Specifications (key-value pairs)
    specifications: Dict[str, str] = field(default_factory=dict)

    # Media
    image_url: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)

    # Metadata
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary."""
        data = asdict(self)
        data['availability'] = self.availability.value
        return data

    def to_json(self) -> str:
        """Convert product to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """Create product from dictionary."""
        if 'availability' in data and isinstance(data['availability'], str):
            data['availability'] = Availability(data['availability'])
        return cls(**data)

    def calculate_discount(self) -> Optional[float]:
        """Calculate discount percentage if not already set."""
        if self.discount_percent is not None:
            return self.discount_percent

        if self.price and self.original_price and self.original_price > self.price:
            self.discount_percent = round(
                ((self.original_price - self.price) / self.original_price) * 100,
                1
            )
            return self.discount_percent

        return None


@dataclass
class SearchRequest:
    """Request model for product search."""
    query: str
    sources: Optional[List[str]] = None  # None means all sources
    max_results: int = 10
    min_price: Optional[float] = None
    max_price: Optional[float] = None


@dataclass
class ProductSearchResult:
    """
    Result container for product search operations.
    """

    query: str
    total_results: int
    products: List[Product]
    sources_searched: List[str]
    search_time_seconds: float
    errors: Dict[str, str] = field(default_factory=dict)  # source -> error message

    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "query": self.query,
            "total_results": self.total_results,
            "products": [p.to_dict() for p in self.products],
            "sources_searched": self.sources_searched,
            "search_time_seconds": round(self.search_time_seconds, 2),
            "errors": self.errors
        }

    def to_json(self) -> str:
        """Convert search result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_csv_rows(self) -> List[Dict[str, Any]]:
        """Convert products to flat CSV-compatible rows."""
        rows = []
        for product in self.products:
            row = {
                "title": product.title,
                "source": product.source,
                "url": product.url,
                "price": product.price,
                "original_price": product.original_price,
                "currency": product.currency,
                "discount_percent": product.discount_percent,
                "availability": product.availability.value,
                "rating": product.rating,
                "rating_count": product.rating_count,
                "brand": product.brand,
                "image_url": product.image_url,
                "scraped_at": product.scraped_at
            }
            # Add top specifications
            for i, (key, value) in enumerate(list(product.specifications.items())[:5]):
                row[f"spec_{i+1}_name"] = key
                row[f"spec_{i+1}_value"] = value
            rows.append(row)
        return rows
