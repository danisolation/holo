"""Trade journal API endpoints.

POST /trades — create trade with auto-calculated fees and FIFO matching
GET /trades — paginated, filterable, sortable trades list
GET /trades/stats — aggregated trade statistics
GET /trades/{trade_id} — single trade detail
DELETE /trades/{trade_id} — delete with lot reversal
"""
from fastapi import APIRouter, HTTPException

from app.database import async_session
from app.services.trade_service import TradeService
from app.schemas.trades import (
    TradeCreate,
    TradeResponse,
    TradesListResponse,
    TradeStatsResponse,
)

router = APIRouter(tags=["trades"])


@router.post("/trades", response_model=TradeResponse, status_code=201)
async def create_trade(data: TradeCreate):
    """Create a new trade with auto-calculated fees.

    BUY creates a lot record. SELL triggers FIFO matching and P&L calculation.
    """
    async with async_session() as session:
        service = TradeService(session)
        try:
            result = await service.create_trade(data)
            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/trades", response_model=TradesListResponse)
async def list_trades(
    page: int = 1,
    page_size: int = 20,
    ticker: str | None = None,
    side: str | None = None,
    sort: str = "trade_date",
    order: str = "desc",
):
    """Get paginated, filterable, sortable trades list."""
    async with async_session() as session:
        service = TradeService(session)
        result = await service.list_trades(
            page=page,
            page_size=page_size,
            ticker=ticker,
            side=side,
            sort=sort,
            order=order,
        )
        return result


@router.get("/trades/stats", response_model=TradeStatsResponse)
async def get_trade_stats():
    """Get aggregated trade statistics: total trades, realized P&L, open positions."""
    async with async_session() as session:
        service = TradeService(session)
        result = await service.get_stats()
        return result


@router.get("/trades/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int):
    """Get a single trade by ID."""
    async with async_session() as session:
        service = TradeService(session)
        result = await service.get_trade(trade_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Trade not found: {trade_id}")
        return result


@router.delete("/trades/{trade_id}", status_code=204)
async def delete_trade(trade_id: int):
    """Delete a trade and handle lot reversal.

    SELL delete: restores consumed lot quantities.
    BUY delete: removes lot (only if unconsumed).
    """
    async with async_session() as session:
        service = TradeService(session)
        try:
            await service.delete_trade(trade_id)
        except ValueError as e:
            msg = str(e)
            status = 404 if "not found" in msg.lower() else 400
            raise HTTPException(status_code=status, detail=msg)
