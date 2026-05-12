"""Simulator API endpoints."""
from fastapi import APIRouter, HTTPException

from app.database import async_session
from app.services.simulator_service import SimulatorService
from app.schemas.simulator import (
    SimulatorTradeCreate,
    SimulatorTradeResponse,
    SimulatorTradesListResponse,
    PortfolioResponse,
    SimulatorStatsResponse,
    PortfolioResetResponse,
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
