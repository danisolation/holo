"""Backtest API: start, status, cancel, trades, equity.

Follows paper_trading.py session-per-request pattern. Per Phase 32.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import select, func as sa_func, text

from app.database import async_session
from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity, BacktestStatus
from app.schemas.backtest import (
    BacktestStartRequest,
    BacktestRunResponse,
    BacktestTradeResponse,
    BacktestTradeListResponse,
    BacktestEquityResponse,
    BacktestEquityListResponse,
    BacktestAnalyticsResponse,
    PerformanceSummaryResponse,
    BenchmarkComparisonResponse,
    BenchmarkPointResponse,
    SectorBreakdownResponse,
    ConfidenceBreakdownResponse,
    TimeframeBreakdownResponse,
)
from app.services.backtest_engine import BacktestEngine
from app.services.backtest_analytics_service import BacktestAnalyticsService

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _run_to_response(run: BacktestRun) -> BacktestRunResponse:
    """Convert BacktestRun ORM object to response schema."""
    return BacktestRunResponse(
        id=run.id,
        start_date=str(run.start_date),
        end_date=str(run.end_date),
        initial_capital=float(run.initial_capital),
        slippage_pct=float(run.slippage_pct),
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        last_completed_date=str(run.last_completed_date) if run.last_completed_date else None,
        total_sessions=run.total_sessions,
        completed_sessions=run.completed_sessions,
        is_cancelled=run.is_cancelled,
        created_at=str(run.created_at),
        updated_at=str(run.updated_at),
    )


@router.post("/runs", status_code=201)
async def start_backtest(request: BacktestStartRequest, bg: BackgroundTasks):
    """BT-01, SIM-01, SIM-03: Start a new backtest run.

    Validates request, enforces singleton (only 1 running at a time),
    counts trading days, creates the run record, and launches the engine
    via BackgroundTasks.
    """
    async with async_session() as session:
        # Singleton check: only 1 backtest running at a time
        result = await session.execute(
            select(BacktestRun).where(BacktestRun.status == BacktestStatus.RUNNING)
        )
        existing = result.scalars().first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="A backtest is already running. Cancel it first or wait for completion.",
            )

        # Count trading days in the date range
        count_result = await session.execute(
            text(
                "SELECT COUNT(DISTINCT date) FROM daily_prices "
                "WHERE date BETWEEN :start AND :end"
            ),
            {"start": request.start_date, "end": request.end_date},
        )
        total_sessions = count_result.scalar() or 0

        # Create the backtest run
        run = BacktestRun(
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            slippage_pct=request.slippage_pct,
            status=BacktestStatus.RUNNING,
            total_sessions=total_sessions,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        # Launch backtest engine in background
        engine = BacktestEngine()
        bg.add_task(engine.run, run.id)

        return {
            "id": run.id,
            "status": run.status.value,
            "total_sessions": run.total_sessions,
        }


@router.get("/runs/latest", response_model=BacktestRunResponse)
async def get_latest_run():
    """Get the most recent backtest run."""
    async with async_session() as session:
        result = await session.execute(
            select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1)
        )
        run = result.scalars().first()
        if not run:
            raise HTTPException(status_code=404, detail="No backtest runs found")
        return _run_to_response(run)


@router.get("/runs/{run_id}", response_model=BacktestRunResponse)
async def get_run(run_id: int):
    """Get backtest run by ID with progress fields."""
    async with async_session() as session:
        result = await session.execute(
            select(BacktestRun).where(BacktestRun.id == run_id)
        )
        run = result.scalars().first()
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        return _run_to_response(run)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: int):
    """BT-05: Cancel a running backtest. Sets is_cancelled flag for graceful stop."""
    async with async_session() as session:
        result = await session.execute(
            select(BacktestRun).where(BacktestRun.id == run_id)
        )
        run = result.scalars().first()
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        if run.status != BacktestStatus.RUNNING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel backtest with status '{run.status.value}'. Only running backtests can be cancelled.",
            )

        run.is_cancelled = True
        await session.commit()
        return {"id": run.id, "is_cancelled": True, "status": run.status.value}


@router.get("/runs/{run_id}/trades", response_model=BacktestTradeListResponse)
async def get_run_trades(
    run_id: int,
    status: str | None = Query(None, description="Filter by trade status"),
    direction: str | None = Query(None, pattern="^(long|bearish)$", description="Filter by direction"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get trades for a backtest run with optional filters."""
    async with async_session() as session:
        # Verify run exists
        run_result = await session.execute(
            select(BacktestRun.id).where(BacktestRun.id == run_id)
        )
        if not run_result.scalars().first():
            raise HTTPException(status_code=404, detail="Backtest run not found")

        # Build query with ticker symbol JOIN
        query = text(
            "SELECT bt.*, t.symbol FROM backtest_trades bt "
            "JOIN tickers t ON bt.ticker_id = t.id "
            "WHERE bt.run_id = :run_id"
        )
        params: dict = {"run_id": run_id}

        count_query = text(
            "SELECT COUNT(*) FROM backtest_trades WHERE run_id = :run_id"
        )
        count_params: dict = {"run_id": run_id}

        # Apply filters via raw SQL additions
        filters = ""
        if status:
            filters += " AND bt.status = :status"
            params["status"] = status
            count_query = text(str(count_query.text) + " AND status = :status")
            count_params["status"] = status
        if direction:
            filters += " AND bt.direction = :direction"
            params["direction"] = direction
            count_query = text(str(count_query.text) + " AND direction = :direction")
            count_params["direction"] = direction

        query = text(str(query.text) + filters + " ORDER BY bt.signal_date DESC LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = offset

        result = await session.execute(query, params)
        rows = result.mappings().all()

        count_result = await session.execute(count_query, count_params)
        total = count_result.scalar() or 0

        trades = [
            BacktestTradeResponse(
                id=row["id"],
                run_id=row["run_id"],
                symbol=row["symbol"],
                backtest_analysis_id=row["backtest_analysis_id"],
                direction=row["direction"],
                status=row["status"],
                entry_price=float(row["entry_price"]),
                stop_loss=float(row["stop_loss"]),
                take_profit_1=float(row["take_profit_1"]),
                take_profit_2=float(row["take_profit_2"]),
                adjusted_stop_loss=float(row["adjusted_stop_loss"]) if row["adjusted_stop_loss"] else None,
                quantity=row["quantity"],
                closed_quantity=row["closed_quantity"],
                realized_pnl=float(row["realized_pnl"]) if row["realized_pnl"] else None,
                realized_pnl_pct=row["realized_pnl_pct"],
                exit_price=float(row["exit_price"]) if row["exit_price"] else None,
                partial_exit_price=float(row["partial_exit_price"]) if row["partial_exit_price"] else None,
                signal_date=str(row["signal_date"]),
                entry_date=str(row["entry_date"]) if row["entry_date"] else None,
                closed_date=str(row["closed_date"]) if row["closed_date"] else None,
                confidence=row["confidence"],
                timeframe=row["timeframe"],
                position_size_pct=row["position_size_pct"],
                risk_reward_ratio=row["risk_reward_ratio"],
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

        return BacktestTradeListResponse(trades=trades, total=total)


@router.get("/runs/{run_id}/equity", response_model=BacktestEquityListResponse)
async def get_run_equity(run_id: int):
    """Get equity curve for a backtest run, ordered by date ASC."""
    async with async_session() as session:
        # Verify run exists
        run_result = await session.execute(
            select(BacktestRun.id).where(BacktestRun.id == run_id)
        )
        if not run_result.scalars().first():
            raise HTTPException(status_code=404, detail="Backtest run not found")

        result = await session.execute(
            select(BacktestEquity)
            .where(BacktestEquity.run_id == run_id)
            .order_by(BacktestEquity.date.asc())
        )
        rows = result.scalars().all()

        equity = [
            BacktestEquityResponse(
                run_id=row.run_id,
                date=str(row.date),
                cash=float(row.cash),
                positions_value=float(row.positions_value),
                total_equity=float(row.total_equity),
                daily_return_pct=row.daily_return_pct,
                cumulative_return_pct=row.cumulative_return_pct,
            )
            for row in rows
        ]

        return BacktestEquityListResponse(equity=equity, total=len(equity))


@router.get("/runs/{run_id}/analytics", response_model=BacktestAnalyticsResponse)
async def get_run_analytics(run_id: int):
    """BENCH-02..05: Performance summary + sector/confidence/timeframe breakdowns."""
    async with async_session() as session:
        svc = BacktestAnalyticsService(session)
        summary = await svc.get_performance_summary(run_id)
        sectors = await svc.get_sector_breakdown(run_id)
        confidence = await svc.get_confidence_breakdown(run_id)
        timeframes = await svc.get_timeframe_breakdown(run_id)

        return BacktestAnalyticsResponse(
            run_id=run_id,
            summary=PerformanceSummaryResponse(**summary),
            sectors=[SectorBreakdownResponse(**s) for s in sectors],
            confidence=[ConfidenceBreakdownResponse(**c) for c in confidence],
            timeframes=[TimeframeBreakdownResponse(**t) for t in timeframes],
        )


@router.get("/runs/{run_id}/benchmark", response_model=BenchmarkComparisonResponse)
async def get_run_benchmark(run_id: int):
    """BENCH-01: AI strategy equity vs VN-Index buy-and-hold comparison."""
    async with async_session() as session:
        svc = BacktestAnalyticsService(session)
        result = await svc.get_benchmark_comparison(run_id)

        return BenchmarkComparisonResponse(
            initial_capital=result["initial_capital"],
            ai_total_return_pct=result["ai_total_return_pct"],
            vnindex_total_return_pct=result.get("vnindex_total_return_pct"),
            outperformance_pct=result.get("outperformance_pct"),
            data=[BenchmarkPointResponse(**d) for d in result["data"]],
        )
