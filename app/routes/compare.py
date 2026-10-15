"""Comparison API. Secrets are request scoped and never returned or persisted."""

import asyncio
import os
import time
from collections import OrderedDict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.models.comparison import CompareRequest, ComparisonResult, Credentials
from app.services.research import ResearchError, ResearchService

router = APIRouter(prefix="/api/compare", tags=["comparison"])
_slots = asyncio.Semaphore(2)
_visitors = OrderedDict()


@router.get("/status")
async def status():
    return {"tavily_configured": bool(os.getenv("TAVILY_API_KEY")),
            "openai_configured": bool(os.getenv("OPENAI_API_KEY"))}


@router.post("", response_model=ComparisonResult)
async def compare(request: Request, body: CompareRequest):
    tavily = os.getenv("TAVILY_API_KEY", "").strip()
    openai = os.getenv("OPENAI_API_KEY", "").strip()
    missing = [name for name, value in [("Tavily", tavily), ("OpenAI", openai)] if not value]
    if missing:
        raise HTTPException(503, {"code": "setup_required", "message": "Comparisons are temporarily unavailable. Please try again later."})
    if any(len(key) > 512 or any(c in key for c in "\r\n") for key in [tavily, openai]):
        raise HTTPException(400, "The API key format is invalid.")
    # Small local guard; use a shared gateway/rate limiter for public deployment.
    visitor = request.client.host if request.client else "unknown"
    current = time.monotonic()
    recent = [t for t in _visitors.pop(visitor, []) if current - t < 60]
    _visitors[visitor] = recent
    if len(recent) >= 5:
        raise HTTPException(429, "Too many comparisons. Please wait a minute.")
    recent.append(current)
    if len(_visitors) > 1000:
        _visitors.popitem(last=False)
    try:
        async with asyncio.timeout(180):
            async with _slots:
                async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
                    service = ResearchService(client, Credentials(tavily=tavily, openai=openai))
                    result = await service.compare(body.query, body.country)
                    return JSONResponse(result.model_dump(), headers={"Cache-Control": "no-store"})
    except ResearchError as exc:
        raise HTTPException(503 if exc.status == 401 else exc.status,
                            "Comparisons are temporarily unavailable. Please try again later."
                            if exc.status == 401 else exc.message) from None
    except TimeoutError:
        raise HTTPException(504, "Research took too long. Try comparing two products.") from None
