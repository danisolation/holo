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
    PortfolioListResponse,
)

router = APIRouter(tags=["simulator"])


def _validate_portfolio_type(portfolio_type: str) -> None:
    """Validate portfolio_type param — reject invalid values (T-107-01)."""
    if portfolio_type not in ("ai", "user"):
        raise HTTPException(status_code=400, detail="portfolio_type must be 'ai' or 'user'")


@router.get("/simulator/portfolios", response_model=PortfolioListResponse)
async def list_portfolios():
    """Get summary of both AI and user portfolios."""
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_all_portfolios_summary()


@router.get("/simulator/portfolio", response_model=PortfolioResponse)
async def get_portfolio(portfolio_type: str = "user"):
    """Get portfolio state with positions and P&L."""
    _validate_portfolio_type(portfolio_type)
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_portfolio(portfolio_name=portfolio_type)


@router.post("/simulator/trades", response_model=SimulatorTradeResponse, status_code=201)
async def create_trade(data: SimulatorTradeCreate):
    """Create a paper trade."""
    async with async_session() as session:
        service = SimulatorService(session)
        try:
            return await service.create_trade(data, portfolio_name=data.portfolio_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/simulator/trades", response_model=SimulatorTradesListResponse)
async def list_trades(page: int = 1, page_size: int = 20, source: str | None = None, portfolio_type: str = "user"):
    """Get paginated trade history. Filter by source: ai_auto or manual."""
    _validate_portfolio_type(portfolio_type)
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.list_trades(page, page_size, source, portfolio_name=portfolio_type)


@router.get("/simulator/stats", response_model=SimulatorStatsResponse)
async def get_stats(portfolio_type: str = "user"):
    """Get AI vs manual performance comparison."""
    _validate_portfolio_type(portfolio_type)
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_stats(portfolio_name=portfolio_type)


@router.get("/simulator/equity-history", response_model=EquityHistoryResponse)
async def get_equity_history(portfolio_type: str = "user"):
    """Get portfolio equity curve over time."""
    _validate_portfolio_type(portfolio_type)
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_equity_history(portfolio_name=portfolio_type)


@router.get("/simulator/pnl-timeline", response_model=PnlTimelineResponse)
async def get_pnl_timeline(portfolio_type: str = "user"):
    """Get all trades with running cumulative P&L."""
    _validate_portfolio_type(portfolio_type)
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.get_pnl_timeline(portfolio_name=portfolio_type)


@router.post("/simulator/reset", response_model=PortfolioResetResponse)
async def reset_portfolio(portfolio_type: str):
    """Reset portfolio to starting capital. Deletes all trades and lots."""
    _validate_portfolio_type(portfolio_type)
    async with async_session() as session:
        service = SimulatorService(session)
        return await service.reset_portfolio(portfolio_name=portfolio_type)


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
    Scoped to AI portfolio (auto-sell only applies to AI positions).
    """
    async with async_session() as session:
        sim_service = SimulatorService(session)
        sl_tp = await sim_service.check_sl_tp_hits(portfolio_name="ai")
        auto_service = AutoTradeService(session)
        signals = await auto_service.execute_sell_signals()
        return {
            "sl_tp_sells": len(sl_tp),
            "signal_sells": len(signals),
            "results": sl_tp + signals,
        }
