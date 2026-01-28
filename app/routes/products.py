"""
Product search API routes.
"""

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.scrapers.manager import get_scraper_manager
from app.models.product import ProductSearchResult

router = APIRouter(prefix="/api/products", tags=["products"])


class SearchRequest(BaseModel):
    """Request model for product search."""

    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    sources: Optional[List[str]] = Field(
        None,
        description="List of sources to search (default: all)"
    )
    max_results: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum results per source"
    )


class SearchResponse(BaseModel):
    """Response model for product search."""

    query: str
    total_results: int
    products: List[dict]
    sources_searched: List[str]
    search_time_seconds: float
    errors: dict


@router.get("/sources")
async def get_available_sources():
    """
    Get list of available product sources.

    Returns:
        List of source names that can be searched
    """
    manager = get_scraper_manager()
    sources = manager.get_available_sources()

    return {
        "sources": sources,
        "count": len(sources)
    }


@router.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    Search for products across multiple sources.

    - **query**: Product search term
    - **sources**: Optional list of specific sources to search
    - **max_results**: Maximum number of results per source (1-50)

    Returns aggregated product data from all searched sources.
    """
    manager = get_scraper_manager()

    try:
        result = await manager.search(
            query=request.query,
            sources=request.sources,
            max_results_per_source=request.max_results
        )

        return SearchResponse(
            query=result.query,
            total_results=result.total_results,
            products=[p.to_dict() for p in result.products],
            sources_searched=result.sources_searched,
            search_time_seconds=result.search_time_seconds,
            errors=result.errors
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_products_get(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    max_results: int = Query(10, ge=1, le=50, description="Max results per source")
):
    """
    Search for products (GET endpoint for simple queries).

    - **q**: Product search term
    - **sources**: Optional comma-separated list of sources
    - **max_results**: Maximum number of results per source
    """
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    request = SearchRequest(
        query=q,
        sources=source_list,
        max_results=max_results
    )

    return await search_products(request)


@router.get("/export/json")
async def export_json(
    q: str = Query(..., min_length=1, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    max_results: int = Query(10, ge=1, le=50)
):
    """
    Search products and export results as JSON file.

    Returns a downloadable JSON file with all product data.
    """
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    manager = get_scraper_manager()
    result = await manager.search(
        query=q,
        sources=source_list,
        max_results_per_source=max_results
    )

    # Create JSON response with download headers
    json_content = result.to_json()
    filename = f"products_{q.replace(' ', '_')[:30]}.json"

    return JSONResponse(
        content=result.to_dict(),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/export/csv")
async def export_csv(
    q: str = Query(..., min_length=1, description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    max_results: int = Query(10, ge=1, le=50)
):
    """
    Search products and export results as CSV file.

    Returns a downloadable CSV file with product data in tabular format.
    """
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",") if s.strip()]

    manager = get_scraper_manager()
    result = await manager.search(
        query=q,
        sources=source_list,
        max_results_per_source=max_results
    )

    # Generate CSV
    rows = result.to_csv_rows()

    if not rows:
        # Return empty CSV with headers
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "title", "source", "url", "price", "original_price",
            "currency", "discount_percent", "availability", "rating",
            "rating_count", "brand", "image_url", "scraped_at"
        ])
        output.seek(0)
    else:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)

    filename = f"products_{q.replace(' ', '_')[:30]}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.delete("/cache")
async def clear_cache():
    """
    Clear the search result cache.

    Useful for refreshing stale data.
    """
    manager = get_scraper_manager()
    manager.clear_cache()

    return {"message": "Cache cleared successfully"}
