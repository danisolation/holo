"""Paper trading API: trade CRUD, manual follow, config, analytics.

Follows portfolio.py session-per-request pattern. Per Phase 24.
"""
from fastapi import APIRouter, HTTPException, Query

from app.database import async_session
from app.services.paper_trade_analytics_service import PaperTradeAnalyticsService
from app.schemas.paper_trading import (
    ManualFollowRequest,
    PaperTradeResponse,
    PaperTradeListResponse,
    SimulationConfigResponse,
    SimulationConfigUpdateRequest,
    AnalyticsSummaryResponse,
    EquityCurveResponse,
    EquityCurvePoint,
    DrawdownResponse,
    DrawdownPeriod,
    DirectionAnalysisItem,
    ConfidenceBracketItem,
    RiskRewardResponse,
    ProfitFactorResponse,
    SectorAnalysisItem,
)

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


@router.get("/trades", response_model=PaperTradeListResponse)
async def list_trades(
    status: str | None = Query(None, description="Filter: pending, active, partial_tp, closed_tp2, closed_sl, closed_timeout, closed_manual"),
    direction: str | None = Query(None, pattern="^(long|bearish)$", description="Filter by direction"),
    timeframe: str | None = Query(None, pattern="^(swing|position)$", description="Filter by timeframe"),
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List paper trades with optional filters and pagination."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.list_trades(
            status=status, direction=direction, timeframe=timeframe,
            symbol=symbol, limit=limit, offset=offset,
        )
        return PaperTradeListResponse(
            trades=[PaperTradeResponse(**t) for t in result["trades"]],
            total=result["total"],
        )


@router.post("/trades/follow", response_model=PaperTradeResponse, status_code=201)
async def create_manual_follow(trade: ManualFollowRequest):
    """PT-09: Manual follow — create paper trade with custom entry/SL/TP.
    ai_analysis_id = NULL (not linked to signal), status = PENDING."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.create_manual_follow(trade.model_dump())
        return PaperTradeResponse(**result)


@router.get("/trades/{trade_id}", response_model=PaperTradeResponse)
async def get_trade(trade_id: int):
    """Get single paper trade detail."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_trade(trade_id)
        return PaperTradeResponse(**result)


@router.post("/trades/{trade_id}/close", response_model=PaperTradeResponse)
async def close_trade(trade_id: int):
    """Manual close — transitions trade to CLOSED_MANUAL."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.close_trade(trade_id)
        return PaperTradeResponse(**result)


@router.get("/config", response_model=SimulationConfigResponse)
async def get_config():
    """Get simulation configuration."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_config()
        return SimulationConfigResponse(**result)


@router.put("/config", response_model=SimulationConfigResponse)
async def update_config(config: SimulationConfigUpdateRequest):
    """Update simulation configuration (partial update — only non-null fields)."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        # Only pass non-null fields
        update_data = {k: v for k, v in config.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        result = await service.update_config(update_data)
        return SimulationConfigResponse(**result)


# --- Analytics Endpoints ---

@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary():
    """AN-01, AN-02: Win rate + total P&L."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_summary()
        return AnalyticsSummaryResponse(**result)


@router.get("/analytics/equity-curve", response_model=EquityCurveResponse)
async def get_equity_curve():
    """AN-03: Equity curve time-series."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_equity_curve()
        return EquityCurveResponse(
            data=[EquityCurvePoint(**p) for p in result["data"]],
            initial_capital=result["initial_capital"],
        )


@router.get("/analytics/drawdown", response_model=DrawdownResponse)
async def get_drawdown():
    """AN-04: Max drawdown with periods."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_drawdown()
        return DrawdownResponse(
            max_drawdown_vnd=result["max_drawdown_vnd"],
            max_drawdown_pct=result["max_drawdown_pct"],
            current_drawdown_vnd=result["current_drawdown_vnd"],
            current_drawdown_pct=result["current_drawdown_pct"],
            periods=[DrawdownPeriod(**p) for p in result["periods"]],
        )


@router.get("/analytics/direction", response_model=list[DirectionAnalysisItem])
async def get_direction_analysis():
    """AN-05: LONG vs BEARISH performance comparison."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_direction_analysis()
        return [DirectionAnalysisItem(**item) for item in result]


@router.get("/analytics/confidence", response_model=list[ConfidenceBracketItem])
async def get_confidence_analysis():
    """AN-06: Performance by confidence bracket (LOW/MEDIUM/HIGH)."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_confidence_analysis()
        return [ConfidenceBracketItem(**item) for item in result]


@router.get("/analytics/risk-reward", response_model=RiskRewardResponse)
async def get_risk_reward():
    """AN-07: R:R achieved vs predicted."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_risk_reward()
        return RiskRewardResponse(**result)


@router.get("/analytics/profit-factor", response_model=ProfitFactorResponse)
async def get_profit_factor():
    """AN-08: Profit factor + expected value per trade."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_profit_factor()
        return ProfitFactorResponse(**result)


@router.get("/analytics/sector", response_model=list[SectorAnalysisItem])
async def get_sector_analysis():
    """AN-09: Performance by industry sector."""
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.get_sector_analysis()
        return [SectorAnalysisItem(**item) for item in result]
