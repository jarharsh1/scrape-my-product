"""
Configuration settings for the Product Intelligence Scraper.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ScraperConfig:
    """Configuration for web scrapers."""

    # Request settings
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    # Rate limiting
    requests_per_minute: int = 30
    burst_limit: int = 5

    # User agent rotation
    rotate_user_agents: bool = True

    # Proxy settings (can be extended for production)
    use_proxies: bool = False
    proxy_list: List[str] = field(default_factory=list)

    # Default headers
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })


@dataclass
class AppConfig:
    """Main application configuration."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # Scraper settings
    scraper: ScraperConfig = field(default_factory=ScraperConfig)

    # Results settings
    max_results_per_source: int = 10
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


# Global configuration instance
config = AppConfig()
