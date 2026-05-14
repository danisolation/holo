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
    EquityHistoryResponse,
    PnlTimelineResponse,
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


@router.get("/simulator/equity-history", response_model=EquityHistoryResponse)
async def get_equity_history():
    """Get portfolio equity curve over time."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_equity_history()


@router.get("/simulator/pnl-timeline", response_model=PnlTimelineResponse)
async def get_pnl_timeline():
    """Get all trades with running cumulative P&L."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_pnl_timeline()


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


@router.post("/simulator/check-auto-sell")
async def trigger_auto_sell_check():
    """Manually trigger SL/TP + AI sell signal check.

    Useful for testing. Runs the same logic as the daily scheduler job.
    """
    async with async_session() as session:
        sim_service = SimulatorService(session)
        sl_tp = await sim_service.check_sl_tp_hits()
        auto_service = AutoTradeService(session)
        signals = await auto_service.execute_sell_signals()
        return {
            "sl_tp_sells": len(sl_tp),
            "signal_sells": len(signals),
            "results": sl_tp + signals,
        }
