"""Ticker and price data endpoints for the dashboard frontend."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, literal_column, text
from sqlalchemy.orm import aliased
from loguru import logger

from app.database import async_session
from app.models.ticker import Ticker
from app.models.daily_price import DailyPrice


# --- Response Schemas ---

class TickerResponse(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    exchange: str = "HOSE"
    market_cap: float | None = None
    is_active: bool = True


class PriceResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketTickerResponse(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    exchange: str = "HOSE"
    market_cap: float | None = None
    last_price: float | None = None
    change_pct: float | None = None


router = APIRouter(prefix="/tickers", tags=["tickers"])

ALLOWED_EXCHANGES = {"HOSE"}


@router.get("/", response_model=list[TickerResponse])
async def list_tickers(
    sector: str | None = Query(None, description="Filter by sector"),
    exchange: str | None = Query(None, description="Filter by exchange: HOSE, HNX, UPCOM"),
    limit: int = Query(100, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """List all active tickers, optionally filtered by sector and/or exchange."""
    if exchange and exchange not in ALLOWED_EXCHANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid exchange. Must be one of: {', '.join(sorted(ALLOWED_EXCHANGES))}",
        )
    async with async_session() as session:
        stmt = select(Ticker).where(Ticker.is_active.is_(True))
        if sector:
            stmt = stmt.where(Ticker.sector == sector)
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)
        stmt = stmt.order_by(Ticker.symbol).offset(offset).limit(limit)
        result = await session.execute(stmt)
        tickers = result.scalars().all()

    return [
        TickerResponse(
            symbol=t.symbol,
            name=t.name,
            sector=t.sector,
            industry=t.industry,
            exchange=t.exchange,
            market_cap=float(t.market_cap) if t.market_cap is not None else None,
            is_active=t.is_active,
        )
        for t in tickers
    ]


@router.get("/sectors", response_model=list[str])
async def list_sectors():
    """Return distinct ICB sector names from active tickers for auto-suggest."""
    async with async_session() as session:
        stmt = (
            select(Ticker.sector)
            .where(Ticker.is_active.is_(True), Ticker.sector.isnot(None))
            .distinct()
            .order_by(Ticker.sector)
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


@router.get("/{symbol}/prices", response_model=list[PriceResponse])
async def get_ticker_prices(
    symbol: str,
    days: int = Query(365, ge=1, le=730, description="Number of days of price history"),
):
    """Get OHLCV price data for a ticker, ordered by date ASC (for charting)."""
    async with async_session() as session:
        # Resolve ticker
        ticker_result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = ticker_result.scalar_one_or_none()
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker '{symbol.upper()}' not found")

        # Query prices
        since = date.today() - timedelta(days=days)
        stmt = (
            select(DailyPrice)
            .where(DailyPrice.ticker_id == ticker.id, DailyPrice.date >= since)
            .order_by(DailyPrice.date.asc())
        )
        result = await session.execute(stmt)
        prices = result.scalars().all()

    result_prices = []
    for p in prices:
        result_prices.append(
            PriceResponse(
                date=p.date.isoformat(),
                open=float(p.open),
                high=float(p.high),
                low=float(p.low),
                close=float(p.close),
                volume=p.volume,
            )
        )
    return result_prices


ALLOWED_SORTS = {"change_pct", "market_cap", "symbol"}
ALLOWED_ORDERS = {"desc", "asc"}


@router.get("/market-overview", response_model=list[MarketTickerResponse])
async def market_overview(
    exchange: str | None = Query(None, description="Filter by exchange: HOSE, HNX, UPCOM"),
    sort: str = Query("change_pct", description="Sort by: change_pct, market_cap, symbol"),
    order: str = Query("desc", description="Order: desc, asc"),
    top: int | None = Query(None, description="Limit to top N results", ge=1, le=500),
):
    """Return all active tickers with latest price and daily change %.

    Uses a ROW_NUMBER() window function to grab the latest 2 daily prices
    per ticker efficiently, then computes change_pct.
    """
    if exchange and exchange not in ALLOWED_EXCHANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid exchange. Must be one of: {', '.join(sorted(ALLOWED_EXCHANGES))}",
        )
    if sort not in ALLOWED_SORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort. Must be one of: {', '.join(sorted(ALLOWED_SORTS))}",
        )
    if order not in ALLOWED_ORDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid order. Must be one of: {', '.join(sorted(ALLOWED_ORDERS))}",
        )
    async with async_session() as session:
        # Subquery: rank prices per ticker by date desc, keep top 2
        ranked = (
            select(
                DailyPrice.ticker_id,
                DailyPrice.close,
                func.row_number()
                .over(
                    partition_by=DailyPrice.ticker_id,
                    order_by=DailyPrice.date.desc(),
                )
                .label("rn"),
            )
            .where(DailyPrice.date >= func.current_date() - 7)
            .subquery("ranked")
        )

        # Latest close (rn=1)
        latest = (
            select(
                ranked.c.ticker_id,
                ranked.c.close.label("last_close"),
            )
            .where(ranked.c.rn == 1)
            .subquery("latest")
        )

        # Previous close (rn=2)
        prev = (
            select(
                ranked.c.ticker_id,
                ranked.c.close.label("prev_close"),
            )
            .where(ranked.c.rn == 2)
            .subquery("prev")
        )

        # Join tickers with latest and previous prices
        stmt = (
            select(
                Ticker.symbol,
                Ticker.name,
                Ticker.sector,
                Ticker.exchange,
                Ticker.market_cap,
                latest.c.last_close,
                prev.c.prev_close,
            )
            .outerjoin(latest, Ticker.id == latest.c.ticker_id)
            .outerjoin(prev, Ticker.id == prev.c.ticker_id)
            .where(Ticker.is_active.is_(True))
        )
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)

        result = await session.execute(stmt)
        rows = result.all()

    items: list[MarketTickerResponse] = []
    for row in rows:
        last_price = float(row.last_close) if row.last_close is not None else None
        prev_close = float(row.prev_close) if row.prev_close is not None else None
        change_pct: float | None = None
        if last_price is not None and prev_close is not None and prev_close != 0:
            change_pct = round((last_price - prev_close) / prev_close * 100, 2)
        items.append(
            MarketTickerResponse(
                symbol=row.symbol,
                name=row.name,
                sector=row.sector,
                exchange=row.exchange,
                market_cap=float(row.market_cap) if row.market_cap is not None else None,
                last_price=last_price,
                change_pct=change_pct,
            )
        )

    # Python-level sorting (change_pct is computed, not in SQL)
    if sort == "change_pct":
        items.sort(key=lambda t: (t.change_pct is None, t.change_pct or 0), reverse=(order == "desc"))
    elif sort == "market_cap":
        items.sort(key=lambda t: (t.market_cap is None, t.market_cap or 0), reverse=(order == "desc"))
    elif sort == "symbol":
        items.sort(key=lambda t: t.symbol, reverse=(order == "desc"))

    # Limit results
    if top is not None:
        items = items[:top]

    return items
