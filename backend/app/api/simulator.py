"""Simulator API endpoints."""
from fastapi import APIRouter, HTTPException

from app.database import async_session
from app.services.simulator_service import SimulatorService
from app.services.auto_trade_service import AutoTradeService
from app.schemas.simulator import (
    SimulatorTradeCreate,
    SimulatorTradeResponse,
    SimulatorTradesListResponse,
    PortfolioResponse,
    SimulatorStatsResponse,
    PortfolioResetResponse,
    PendingSignalResponse,
    ExecuteSignalsRequest,
)

router = APIRouter(tags=["simulator"])


@router.get("/simulator/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get portfolio state with positions and P&L."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_portfolio()


@router.post("/simulator/trades", response_model=SimulatorTradeResponse, status_code=201)
async def create_trade(data: SimulatorTradeCreate):
    """Create a paper trade."""
    async with async_session() as session:
        service = SimulatorService(session)
        try:
            return await service.create_trade(data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/simulator/trades", response_model=SimulatorTradesListResponse)
async def list_trades(page: int = 1, page_size: int = 20, source: str | None = None):
    """Get paginated trade history. Filter by source: ai_auto or manual."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.list_trades(page, page_size, source)


@router.get("/simulator/stats", response_model=SimulatorStatsResponse)
async def get_stats():
    """Get AI vs manual performance comparison."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_stats()


@router.post("/simulator/reset", response_model=PortfolioResetResponse)
async def reset_portfolio():
    """Reset portfolio to starting capital. Deletes all trades and lots."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.reset_portfolio()


@router.get("/simulator/signals/pending", response_model=list[PendingSignalResponse])
async def get_pending_signals(days_back: int = 3):
    """Get AI signals that haven't been traded yet."""
    async with async_session() as session:
        service = AutoTradeService(session)
        return await service.get_pending_signals(days_back)


@router.post("/simulator/signals/execute")
async def execute_signals(data: ExecuteSignalsRequest):
    """Execute BUY trades for specified AI signal pick IDs."""
    async with async_session() as session:
        service = AutoTradeService(session)
        try:
            results = await service.execute_ai_signals(data.pick_ids)
            return {"executed": len([r for r in results if "error" not in r]), "results": results}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/simulator/signals/skip")
async def skip_signals(data: ExecuteSignalsRequest):
    """Mark AI signals as skipped."""
    async with async_session() as session:
        service = AutoTradeService(session)
        count = await service.skip_signals(data.pick_ids)
        return {"skipped": count}
