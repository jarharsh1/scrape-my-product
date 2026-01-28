# Product Intelligence Web Scraping Tool

A powerful, modular web scraping application for gathering product information from multiple e-commerce sources. Built with Python (FastAPI) backend and vanilla HTML/CSS/JavaScript frontend.

## Features

- **Multi-Source Search**: Search products across Amazon, eBay, Best Buy, and Walmart simultaneously
- **Structured Data Extraction**: Extract product title, price, discount, availability, ratings, specifications, images, and more
- **Data Normalization**: Clean and standardize data from different sources
- **Export Options**: Download results as JSON or CSV
- **Rate Limiting**: Built-in rate limiting to prevent overwhelming target sites
- **Modular Architecture**: Easy to add new scrapers or integrate as an API module
- **Professional UI**: Clean, responsive interface with loading states and error handling

## Project Structure

```
scrape-my-product/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── routes/
│   │   ├── __init__.py
│   │   └── products.py      # API routes for product search
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py          # Base scraper class
│   │   ├── amazon.py        # Amazon scraper
│   │   ├── ebay.py          # eBay scraper
│   │   ├── bestbuy.py       # Best Buy scraper
│   │   ├── demo.py          # Demo scrapers for testing
│   │   └── manager.py       # Scraper orchestration manager
│   ├── models/
│   │   ├── __init__.py
│   │   └── product.py       # Product data models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── rate_limiter.py  # Rate limiting implementation
│   │   └── data_cleaner.py  # Data cleaning utilities
│   └── static/
│       ├── css/
│       │   └── style.css    # Application styles
│       └── js/
│           └── app.js       # Frontend JavaScript
├── templates/
│   └── index.html           # Main HTML template
├── requirements.txt
├── run.py                   # Application entry point
└── README.md
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd scrape-my-product
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Development Mode

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at: **http://localhost:8000**

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Usage

### Web Interface

1. Open your browser and navigate to `http://localhost:8000`
2. Enter a product name in the search box (e.g., "wireless headphones")
3. Select which sources to search (all selected by default)
4. Click "Search" and wait for results
5. View results in the table, click columns to sort
6. Double-click a row to see product details
7. Export results as JSON or CSV using the export buttons

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/products/search` | POST | Search products across sources |
| `/api/products/search` | GET | Search products (query params) |
| `/api/products/sources` | GET | List available sources |
| `/api/products/export/json` | GET | Export search results as JSON |
| `/api/products/export/csv` | GET | Export search results as CSV |
| `/api/docs` | GET | Interactive API documentation |
| `/health` | GET | Health check endpoint |

### API Examples

**Search products (POST)**:
```bash
curl -X POST "http://localhost:8000/api/products/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "wireless headphones", "sources": ["amazon", "ebay"], "max_results": 10}'
```

**Search products (GET)**:
```bash
curl "http://localhost:8000/api/products/search?q=wireless+headphones&sources=amazon,ebay&max_results=10"
```

**Export as JSON**:
```bash
curl "http://localhost:8000/api/products/export/json?q=laptop" -o products.json
```

**Export as CSV**:
```bash
curl "http://localhost:8000/api/products/export/csv?q=laptop" -o products.csv
```

## Configuration

Edit `app/config.py` to customize settings:

```python
@dataclass
class ScraperConfig:
    request_timeout: int = 30          # Request timeout in seconds
    max_retries: int = 3               # Number of retry attempts
    retry_delay: float = 1.0           # Delay between retries
    requests_per_minute: int = 30      # Rate limit
    burst_limit: int = 5               # Burst request limit

@dataclass
class AppConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    max_results_per_source: int = 10
    enable_caching: bool = True
    cache_ttl_seconds: int = 300       # 5 minutes
```

## Demo Mode vs Real Scraping

By default, the application uses **demo scrapers** that return simulated product data. This is ideal for:
- Development and testing
- Demonstrations
- Avoiding rate limiting issues

To use **real scrapers** that fetch from actual e-commerce sites:

1. Edit `app/scrapers/manager.py`:
   ```python
   def get_scraper_manager(use_demo: bool = False) -> ScraperManager:  # Change to False
   ```

2. Note: Real scrapers may be blocked by some e-commerce sites. Consider using:
   - Proxy rotation
   - Longer delays between requests
   - Headless browser automation (Selenium/Playwright) for complex sites

## Adding a New Scraper

1. Create a new file in `app/scrapers/` (e.g., `newegg.py`):

```python
from app.scrapers.base import BaseScraper
from app.models.product import Product

class NeweggScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "newegg"

    @property
    def base_url(self) -> str:
        return "https://www.newegg.com"

    async def search(self, query: str, max_results: int = 10) -> list[Product]:
        # Implement scraping logic
        pass
```

2. Register the scraper in `app/scrapers/manager.py`:

```python
from app.scrapers.newegg import NeweggScraper

@dataclass
class ScraperRegistry:
    real_scrapers: Dict[str, Type[BaseScraper]] = field(default_factory=lambda: {
        # ... existing scrapers ...
        "newegg": NeweggScraper,
    })
```

## Data Model

The `Product` model includes the following fields:

| Field | Type | Description |
|-------|------|-------------|
| title | str | Product title |
| source | str | Source website name |
| url | str | Product page URL |
| price | float | Current price |
| original_price | float | Original price (before discount) |
| currency | str | Currency code (default: USD) |
| discount_percent | float | Discount percentage |
| availability | enum | IN_STOCK, OUT_OF_STOCK, LIMITED, PRE_ORDER, UNKNOWN |
| rating | float | Rating out of 5 |
| rating_count | int | Number of ratings |
| review_count | int | Number of reviews |
| brand | str | Product brand |
| sku | str | Stock keeping unit |
| specifications | dict | Key-value specifications |
| image_url | str | Main product image URL |
| scraped_at | str | ISO timestamp of scrape |

## Architecture Notes

### For API Integration

This tool is designed to be modular and can be easily integrated into a larger application:

```python
from app.scrapers.manager import ScraperManager

# Create manager instance
manager = ScraperManager(use_demo_scrapers=True)

# Search for products
result = await manager.search(
    query="laptop",
    sources=["amazon", "ebay"],
    max_results_per_source=10
)

# Access results
for product in result.products:
    print(f"{product.title}: ${product.price}")
```

### Key Components

- **ScraperManager**: Orchestrates concurrent scraping from multiple sources
- **BaseScraper**: Abstract base class with common functionality (HTTP, rate limiting, parsing)
- **DataCleaner**: Normalizes prices, ratings, and other data across sources
- **RateLimiter**: Token bucket algorithm for request throttling

## Troubleshooting

### Common Issues

1. **No results returned**
   - Check your internet connection
   - Verify the search query is valid
   - Some sites may block scrapers; try demo mode

2. **Slow searches**
   - This is normal; multiple sites are being scraped concurrently
   - Reduce the number of sources or max results

3. **Rate limiting errors**
   - The application has built-in rate limiting
   - If issues persist, increase delays in config

4. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Verify you're using Python 3.9+

## License

This project is provided for educational purposes. Respect the terms of service of any websites you scrape.

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style patterns
- New scrapers extend the `BaseScraper` class
- All new features include appropriate error handling
