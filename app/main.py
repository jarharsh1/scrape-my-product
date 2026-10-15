"""
Main FastAPI application for the Product Intelligence Scraper.
"""

import logging
import os
import re
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, PlainTextResponse

load_dotenv()

from app.routes import products_router
from app.routes.compare import router as compare_router
from app.scrapers.manager import shutdown_manager
from app.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info("Starting Product Intelligence Scraper...")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await shutdown_manager()


# Create FastAPI app
app = FastAPI(
    title="Product Intelligence Scraper",
    description="A powerful tool for scraping and aggregating product information from multiple e-commerce sources.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routes
app.include_router(products_router)
app.include_router(compare_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse(request=request, name="compare.html",
        context={"adsense_publisher_id": adsense_publisher_id()})


@app.get("/legacy", response_class=HTMLResponse)
async def legacy(request: Request):
    return templates.TemplateResponse(request=request, name="index.html",
                                     context={"title": "Product Intelligence Scraper"})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Product Intelligence Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/products/search",
            "sources": "/api/products/sources",
            "export_json": "/api/products/export/json",
            "export_csv": "/api/products/export/csv",
            "documentation": "/api/docs"
        }
    }


def adsense_publisher_id():
    value = os.getenv("ADSENSE_PUBLISHER_ID", "").strip()
    return value if re.fullmatch(r"ca-pub-\d{16}", value) else ""


@app.get("/ads.txt", response_class=PlainTextResponse)
async def ads_txt():
    publisher = adsense_publisher_id()
    if not publisher:
        return PlainTextResponse("Advertising is not configured.\n", status_code=404)
    return PlainTextResponse(f"google.com, {publisher[3:]}, DIRECT, f08c47fec0942fa0\n")
