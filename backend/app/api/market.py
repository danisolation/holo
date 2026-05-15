"""Market API — breadth indicators + sector analysis for HOSE.

Endpoints:
- GET /breadth — A/D line, MA breadth, 52-week highs/lows (Phase 100)
- GET /sectors — avg % price change per sector for today/7D/30D (Phase 101)
- GET /sector-flow — net volume per sector per day (Phase 101)
- GET /peer-analysis/{symbol} — AI peer analysis via Gemini (Phase 106)

All endpoints use TTLCache (300s) to avoid repeated heavy computation.
"""
from datetime import date, timedelta

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.database import async_session
from app.schemas.market_breadth import MarketBreadthResponse
from app.schemas.screener import ScreenerResponse, PeerComparisonResponse, SectorDetailResponse
from app.schemas.sector import SectorPerformanceItem, SectorFlowItem, SectorAnalysisAPIResponse
from app.services.market_breadth_service import MarketBreadthService
from app.services.screener_service import ScreenerService
from app.services.sector_analysis_service import SectorAnalysisService

router = APIRouter(prefix="/market", tags=["market"])

# TTLCache: 300s TTL, 16 entries for different date range combos
_breadth_cache: TTLCache = TTLCache(maxsize=16, ttl=300)
_sector_perf_cache: TTLCache = TTLCache(maxsize=8, ttl=300)
_sector_flow_cache: TTLCache = TTLCache(maxsize=16, ttl=300)
_sector_detail_cache: TTLCache = TTLCache(maxsize=16, ttl=300)
_peers_cache: TTLCache = TTLCache(maxsize=32, ttl=300)


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


# --- Sector Enrichment ---

@router.post("/enrich-sectors")
async def enrich_sectors():
    """Manually trigger sector/industry enrichment from Fireant ICB data.

    Fetches ICB codes for all active tickers and maps to Vietnamese
    sector/industry names. Use when sector data is stale or missing.
    """
    async with async_session() as session:
        from app.services.ticker_service import TickerService
        service = TickerService(session)
        result = await service.enrich_sectors_from_fireant()
    return result


# --- Phase 104: Screening & Comparison APIs ---


@router.get("/screener", response_model=ScreenerResponse)
async def screen_tickers(
    sector: str | None = Query(None),
    industry: str | None = Query(None),
    min_volume: int | None = Query(None, ge=0),
    max_volume: int | None = Query(None, ge=0),
    min_change: float | None = Query(None, description="Min 1D % change"),
    max_change: float | None = Query(None, description="Max 1D % change"),
    min_pe: float | None = Query(None, ge=0),
    max_pe: float | None = Query(None, ge=0),
    sort_by: str = Query("volume", description="Sort column: volume, change_1d, change_7d, change_30d, pe, close, market_cap"),
    sort_order: str = Query("desc", description="asc or desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ScreenerResponse:
    """Screen tickers by sector, industry, volume, % change, and P/E filters.

    Returns paginated results sorted by the specified metric.
    NOT cached — filter params vary too much.
    """
    async with async_session() as session:
        service = ScreenerService(session)
        result = await service.screen_tickers(
            sector=sector,
            industry=industry,
            min_volume=min_volume,
            max_volume=max_volume,
            min_change=min_change,
            max_change=max_change,
            min_pe=min_pe,
            max_pe=max_pe,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
    return ScreenerResponse(**result)


@router.get("/sector/{sector_name}", response_model=SectorDetailResponse)
async def get_sector_detail(sector_name: str) -> SectorDetailResponse:
    """Get all tickers in a sector with latest price and 7D/30D performance.

    Cached for 300 seconds per sector name.
    """
    cache_key = sector_name
    cached = _sector_detail_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        service = ScreenerService(session)
        result = await service.get_sector_detail(sector_name)

    response = SectorDetailResponse(**result)
    _sector_detail_cache[cache_key] = response
    return response



# --- Phase 106: AI Peer Analysis ---

_peer_analysis_cache: TTLCache = TTLCache(maxsize=64, ttl=600)


@router.get("/peer-analysis/{symbol}")
async def get_peer_analysis(symbol: str):
    """Get AI-powered peer analysis comparing a ticker to its sector peers.

    Returns structured Vietnamese analysis with strengths, weaknesses,
    overall verdict, peer position, and recommendation.
    Cached for 600 seconds to avoid repeated Gemini calls.
    """
    upper = symbol.upper()
    cached = _peer_analysis_cache.get(upper)
    if cached is not None:
        return cached

    async with async_session() as session:
        from app.services.peer_analysis_service import PeerAnalysisService
        service = PeerAnalysisService(session)
        try:
            result = await service.analyze(upper)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Peer analysis failed for {upper}: {e}")
            raise HTTPException(status_code=502, detail="AI analysis temporarily unavailable")

    _peer_analysis_cache[upper] = result
    return result


@router.get("/peers/{symbol}", response_model=PeerComparisonResponse)
async def get_peer_comparison(symbol: str) -> PeerComparisonResponse:
    """Get peer comparison for a ticker — ranked metrics among sector peers.

    Cached for 300 seconds per symbol.
    Returns 404 if ticker not found or has no sector.
    """
    cache_key = symbol.upper()
    cached = _peers_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        service = ScreenerService(session)
        try:
            result = await service.get_peer_comparison(symbol)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    response = PeerComparisonResponse(**result)
    _peers_cache[cache_key] = response
    return response
