"""Market breadth API — market-wide health indicators for HOSE.

Returns A/D line, MA breadth (% above MA50/MA200), and 52-week highs/lows
for configurable date range. Single endpoint returns all 3 metrics.
TTLCache (300s) to avoid repeated heavy computation.
"""
from datetime import date, timedelta

from cachetools import TTLCache
from fastapi import APIRouter, Query

from app.database import async_session
from app.schemas.market_breadth import MarketBreadthResponse
from app.services.market_breadth_service import MarketBreadthService

router = APIRouter(prefix="/market", tags=["market"])

# TTLCache: 300s TTL, 16 entries for different date range combos
_breadth_cache: TTLCache = TTLCache(maxsize=16, ttl=300)


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
