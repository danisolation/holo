"""Portfolio management endpoints: trade entry, holdings, summary, trade history."""
from fastapi import APIRouter, HTTPException, Query

from app.database import async_session
from app.services.portfolio_service import PortfolioService
from app.schemas.portfolio import (
    TradeRequest,
    TradeResponse,
    HoldingResponse,
    PortfolioSummaryResponse,
    TradeHistoryResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/trades", response_model=TradeResponse, status_code=201)
async def create_trade(trade: TradeRequest):
    """Record a buy or sell trade."""
    async with async_session() as session:
        service = PortfolioService(session)
        try:
            result = await service.record_trade(
                symbol=trade.symbol,
                side=trade.side,
                quantity=trade.quantity,
                price=trade.price,
                trade_date=trade.trade_date,
                fees=trade.fees,
            )
            return TradeResponse(**result)
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            raise HTTPException(status_code=400, detail=error_msg)


@router.get("/holdings", response_model=list[HoldingResponse])
async def get_holdings():
    """Get current holdings with per-position P&L."""
    async with async_session() as session:
        service = PortfolioService(session)
        holdings = await service.get_holdings()
        return [HoldingResponse(**h) for h in holdings]


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_summary():
    """Get portfolio summary: total invested, market value, return %."""
    async with async_session() as session:
        service = PortfolioService(session)
        summary = await service.get_summary()
        return PortfolioSummaryResponse(**summary)


@router.get("/trades", response_model=TradeHistoryResponse)
async def get_trades(
    ticker: str | None = Query(None, description="Filter by ticker symbol"),
    side: str | None = Query(None, pattern="^(BUY|SELL)$", description="Filter by side"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get trade history with optional filtering."""
    async with async_session() as session:
        service = PortfolioService(session)
        result = await service.get_trades(
            ticker_symbol=ticker, side=side, limit=limit, offset=offset
        )
        return TradeHistoryResponse(
            trades=[TradeResponse(**t) for t in result["trades"]],
            total=result["total"],
        )
