"""Ticker and price data endpoints for the dashboard frontend."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
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
    market_cap: float | None = None
    is_active: bool = True


class PriceResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


router = APIRouter(prefix="/tickers", tags=["tickers"])


@router.get("/", response_model=list[TickerResponse])
async def list_tickers(sector: str | None = Query(None, description="Filter by sector")):
    """List all active tickers, optionally filtered by sector."""
    async with async_session() as session:
        stmt = select(Ticker).where(Ticker.is_active.is_(True))
        if sector:
            stmt = stmt.where(Ticker.sector == sector)
        stmt = stmt.order_by(Ticker.symbol)
        result = await session.execute(stmt)
        tickers = result.scalars().all()

    return [
        TickerResponse(
            symbol=t.symbol,
            name=t.name,
            sector=t.sector,
            industry=t.industry,
            market_cap=float(t.market_cap) if t.market_cap is not None else None,
            is_active=t.is_active,
        )
        for t in tickers
    ]


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

    return [
        PriceResponse(
            date=p.date.isoformat(),
            open=float(p.open),
            high=float(p.high),
            low=float(p.low),
            close=float(p.close),
            volume=p.volume,
        )
        for p in prices
    ]
