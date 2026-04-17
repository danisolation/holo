"""Portfolio management endpoints: trade entry, holdings, summary, trade history,
performance analytics, allocation breakdown, trade edit/delete, CSV import."""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from app.database import async_session
from app.services.portfolio_service import PortfolioService
from app.services.csv_import_service import CSVImportService
from app.schemas.portfolio import (
    TradeRequest,
    TradeResponse,
    TradeUpdateRequest,
    HoldingResponse,
    PortfolioSummaryResponse,
    TradeHistoryResponse,
    PerformanceResponse,
    PerformanceDataPoint,
    AllocationResponse,
    AllocationItem,
    CSVDryRunResponse,
    CSVImportResponse,
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


# --- Analytics endpoints (PORT-09, PORT-10) ---


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    period: str = Query("3M", pattern="^(1M|3M|6M|1Y|ALL)$", description="Chart period"),
):
    """Get daily portfolio value snapshots for performance chart. Per PORT-09."""
    async with async_session() as session:
        service = PortfolioService(session)
        data = await service.get_performance_data(period)
        return PerformanceResponse(
            data=[PerformanceDataPoint(**d) for d in data],
            period=period,
        )


@router.get("/allocation", response_model=AllocationResponse)
async def get_allocation(
    mode: str = Query("ticker", pattern="^(ticker|sector)$", description="Group by ticker or sector"),
):
    """Get portfolio allocation by ticker or sector. Per PORT-10."""
    async with async_session() as session:
        service = PortfolioService(session)
        data = await service.get_allocation_data(mode)
        total_value = sum(item["value"] for item in data) if data else 0
        return AllocationResponse(
            data=[AllocationItem(**d) for d in data],
            mode=mode,
            total_value=total_value,
        )


# --- Trade edit/delete endpoints (PORT-11) ---


@router.put("/trades/{trade_id}", response_model=TradeResponse)
async def update_trade(trade_id: int, trade: TradeUpdateRequest):
    """Update an existing trade. Triggers FIFO recalculation. Per PORT-11."""
    async with async_session() as session:
        service = PortfolioService(session)
        try:
            result = await service.update_trade(
                trade_id=trade_id,
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


@router.delete("/trades/{trade_id}")
async def delete_trade(trade_id: int):
    """Delete a trade and recalculate FIFO lots. Per PORT-11."""
    async with async_session() as session:
        service = PortfolioService(session)
        try:
            result = await service.delete_trade(trade_id)
            return result
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            raise HTTPException(status_code=400, detail=error_msg)


# --- CSV import endpoint (PORT-12) ---


@router.post("/import")
async def import_trades(
    file: UploadFile = File(...),
    dry_run: bool = Query(True, description="If true, validate only; if false, import trades"),
):
    """Import trades from broker CSV. Per PORT-12.
    dry_run=true: parse and validate, return preview.
    dry_run=false: import valid trades."""
    # Read file content
    content = await file.read()

    # T-13-08 mitigation: enforce max size (5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")

    try:
        csv_text = content.decode("utf-8")
    except UnicodeDecodeError:
        # Try common Vietnamese encoding
        try:
            csv_text = content.decode("cp1252")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Cannot decode CSV file. Use UTF-8 or Windows-1252 encoding.",
            )

    async with async_session() as session:
        csv_service = CSVImportService(session)
        try:
            if dry_run:
                result = await csv_service.dry_run(csv_text)
                return result
            else:
                portfolio_service = PortfolioService(session)
                result = await csv_service.import_trades(csv_text, portfolio_service)
                return CSVImportResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
