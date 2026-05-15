"""Market API — breadth indicators + sector analysis for HOSE.

Endpoints:
- GET /breadth — A/D line, MA breadth, 52-week highs/lows (Phase 100)
- GET /sectors — avg % price change per sector for today/7D/30D (Phase 101)
- GET /sector-flow — net volume per sector per day (Phase 101)

All endpoints use TTLCache (300s) to avoid repeated heavy computation.
"""
from datetime import date, timedelta

from cachetools import TTLCache
from fastapi import APIRouter, Query

from app.database import async_session
from app.schemas.market_breadth import MarketBreadthResponse
from app.schemas.sector import SectorPerformanceItem, SectorFlowItem, SectorAnalysisAPIResponse
from app.services.market_breadth_service import MarketBreadthService
from app.services.sector_analysis_service import SectorAnalysisService

router = APIRouter(prefix="/market", tags=["market"])

# TTLCache: 300s TTL, 16 entries for different date range combos
_breadth_cache: TTLCache = TTLCache(maxsize=16, ttl=300)
_sector_perf_cache: TTLCache = TTLCache(maxsize=8, ttl=300)
_sector_flow_cache: TTLCache = TTLCache(maxsize=16, ttl=300)


@router.get("/breadth", response_model=MarketBreadthResponse)
async def get_market_breadth(
    start_date: date | None = Query(None, description="Start date (default: 90 days ago)"),
    end_date: date | None = Query(None, description="End date (default: today)"),
) -> MarketBreadthResponse:
    """Get market breadth indicators for HOSE.

    Returns daily A/D line, MA breadth, and 52-week highs/lows.
    Default range: last 90 days.
    """
    today = date.today()
    _end = end_date or today
    _start = start_date or (_end - timedelta(days=90))

    cache_key = f"{_start}:{_end}"
    cached = _breadth_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        service = MarketBreadthService(session)
        result = await service.get_all_breadth(_start, _end)

    response = MarketBreadthResponse(**result)
    _breadth_cache[cache_key] = response
    return response


@router.get("/sectors", response_model=list[SectorPerformanceItem])
async def get_sector_performance(
    start_date: date | None = Query(None, description="Start date (default: 30 days ago)"),
    end_date: date | None = Query(None, description="End date (default: today)"),
) -> list[SectorPerformanceItem]:
    """Get average % price change per sector for today, 7D, and 30D.

    Returns sector-level aggregated performance data for the heatmap.
    Date range clamped to max 365 days to prevent heavy queries.
    """
    today = date.today()
    _end = end_date or today
    _start = start_date or (_end - timedelta(days=30))

    # Clamp range to max 365 days (T-101-01 threat mitigation)
    if (_end - _start).days > 365:
        _start = _end - timedelta(days=365)

    cache_key = f"{_start}_{_end}"
    cached = _sector_perf_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        service = SectorAnalysisService(session)
        result = await service.get_sector_performance(_start, _end)

    response = [SectorPerformanceItem(**item) for item in result]
    _sector_perf_cache[cache_key] = response
    return response


@router.get("/sector-flow", response_model=list[SectorFlowItem])
async def get_sector_flow(
    start_date: date | None = Query(None, description="Start date (default: 7 days ago)"),
    end_date: date | None = Query(None, description="End date (default: today)"),
) -> list[SectorFlowItem]:
    """Get net buying/selling volume per sector per day.

    Returns sector-level flow data for rotation analysis.
    Date range clamped to max 365 days to prevent heavy queries.
    """
    today = date.today()
    _end = end_date or today
    _start = start_date or (_end - timedelta(days=7))

    # Clamp range to max 365 days (T-101-01 threat mitigation)
    if (_end - _start).days > 365:
        _start = _end - timedelta(days=365)

    cache_key = f"{_start}_{_end}"
    cached = _sector_flow_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        service = SectorAnalysisService(session)
        result = await service.get_sector_flow(_start, _end)

    response = [SectorFlowItem(**item) for item in result]
    _sector_flow_cache[cache_key] = response
    return response


# --- Phase 103: AI Sector Intelligence ---

_sector_analysis_cache: TTLCache = TTLCache(maxsize=1, ttl=600)


@router.get("/sector-analysis", response_model=SectorAnalysisAPIResponse)
async def get_sector_analysis() -> SectorAnalysisAPIResponse:
    """Get latest AI sector intelligence analysis.

    Returns Gemini's sector strength/weakness analysis and rotation timing.
    Updated daily after the price crawl pipeline completes.
    """
    cached = _sector_analysis_cache.get("latest")
    if cached is not None:
        return cached

    async with async_session() as session:
        from app.services.sector_intelligence_service import SectorIntelligenceService
        service = SectorIntelligenceService(session)
        result = await service.get_latest()

    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No sector analysis available yet")

    response = SectorAnalysisAPIResponse(**result)
    _sector_analysis_cache["latest"] = response
    return response
