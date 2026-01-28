"""Web scrapers for various e-commerce sites."""

from app.scrapers.base import BaseScraper
from app.scrapers.manager import ScraperManager

__all__ = ["BaseScraper", "ScraperManager"]
