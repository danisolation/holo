"""Discovery API — scored tickers for stock discovery page.

Returns latest-date discovery results with optional sector/signal filtering.
Single JOIN query (no N+1). Decimal→float conversion for JSON safety.
"""
from cachetools import TTLCache
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select, func

from app.database import async_session
from app.models.discovery_result import DiscoveryResult
from app.models.ticker import Ticker


class DiscoveryItemResponse(BaseModel):
    """Response model for a single discovery result."""
    symbol: str
    name: str
    sector: str | None = None
    score_date: str
    rsi_score: float | None = None
    macd_score: float | None = None
    adx_score: float | None = None
    volume_score: float | None = None
    pe_score: float | None = None
    roe_score: float | None = None
    total_score: float
    dimensions_scored: int


# Signal column mapping for signal_type filter
SIGNAL_COLUMNS = {
    "rsi": DiscoveryResult.rsi_score,
    "macd": DiscoveryResult.macd_score,
    "adx": DiscoveryResult.adx_score,
    "volume": DiscoveryResult.volume_score,
    "pe": DiscoveryResult.pe_score,
    "roe": DiscoveryResult.roe_score,
}

SIGNAL_THRESHOLD = 7.0

router = APIRouter(prefix="/discovery", tags=["discovery"])

# In-memory cache for discovery — 120s TTL, 32 entries for filter combos
_discovery_cache: TTLCache = TTLCache(maxsize=32, ttl=120)


@router.get("/", response_model=list[DiscoveryItemResponse])
async def get_discovery(
    sector: str | None = Query(None, description="Filter by ICB sector name"),
    signal_type: str | None = Query(None, description="Filter by signal dimension (rsi, macd, adx, volume, pe, roe)"),
    min_score: float = Query(0, ge=0, le=10, description="Minimum total_score"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
) -> list[DiscoveryItemResponse]:
    """Get discovery results from the latest score_date.

    Joins discovery_results with tickers to return symbol/name/sector.
    Supports filtering by sector, signal type (score >= 7), and minimum total score.
    """
    cache_key = f"{sector}:{signal_type}:{min_score}:{limit}"
    cached = _discovery_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        # Step 1: Get latest score_date
        latest_date_stmt = select(func.max(DiscoveryResult.score_date))
        latest_date_result = await session.execute(latest_date_stmt)
        latest_date = latest_date_result.scalar_one_or_none()

        if latest_date is None:
            return []

        # Step 2: Main query — JOIN discovery_results with tickers
        stmt = (
            select(
                Ticker.symbol,
                Ticker.name,
                Ticker.sector,
                DiscoveryResult.score_date,
                DiscoveryResult.rsi_score,
                DiscoveryResult.macd_score,
                DiscoveryResult.adx_score,
                DiscoveryResult.volume_score,
                DiscoveryResult.pe_score,
                DiscoveryResult.roe_score,
                DiscoveryResult.total_score,
                DiscoveryResult.dimensions_scored,
            )
            .join(Ticker, DiscoveryResult.ticker_id == Ticker.id)
            .where(DiscoveryResult.score_date == latest_date)
            .where(DiscoveryResult.total_score >= min_score)
        )

        # Optional: sector filter
        if sector:
            stmt = stmt.where(Ticker.sector == sector)

        # Optional: signal_type filter — column must be non-NULL and >= threshold
        if signal_type and signal_type in SIGNAL_COLUMNS:
            col = SIGNAL_COLUMNS[signal_type]
            stmt = stmt.where(col.isnot(None)).where(col >= SIGNAL_THRESHOLD)

        stmt = stmt.order_by(DiscoveryResult.total_score.desc()).limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

        # Convert Decimal fields to float for JSON serialization
        items = [
            DiscoveryItemResponse(
                symbol=row.symbol,
                name=row.name,
                sector=row.sector,
                score_date=row.score_date.isoformat(),
                rsi_score=float(row.rsi_score) if row.rsi_score is not None else None,
                macd_score=float(row.macd_score) if row.macd_score is not None else None,
                adx_score=float(row.adx_score) if row.adx_score is not None else None,
                volume_score=float(row.volume_score) if row.volume_score is not None else None,
                pe_score=float(row.pe_score) if row.pe_score is not None else None,
                roe_score=float(row.roe_score) if row.roe_score is not None else None,
                total_score=float(row.total_score),
                dimensions_scored=row.dimensions_scored,
            )
            for row in rows
        ]

    _discovery_cache[cache_key] = items
    return items
