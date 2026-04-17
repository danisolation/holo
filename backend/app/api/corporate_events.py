"""Corporate events calendar API endpoint (CORP-08).

Provides GET /api/corporate-events with month, type, and symbol filters
for the frontend calendar view.
"""
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, extract
from loguru import logger

from app.database import async_session
from app.models.corporate_event import CorporateEvent
from app.models.ticker import Ticker


ALLOWED_EVENT_TYPES = {"CASH_DIVIDEND", "STOCK_DIVIDEND", "BONUS_SHARES", "RIGHTS_ISSUE"}

router = APIRouter(prefix="/corporate-events", tags=["corporate-events"])


class CorporateEventResponse(BaseModel):
    """Response schema for corporate events."""
    id: int
    symbol: str
    name: str
    event_type: str
    ex_date: str
    record_date: str | None = None
    announcement_date: str | None = None
    dividend_amount: float | None = None
    ratio: float | None = None
    note: str | None = None


@router.get("/", response_model=list[CorporateEventResponse])
async def list_corporate_events(
    month: str | None = Query(None, description="Filter by month: YYYY-MM format"),
    type: str | None = Query(None, description="Filter by event type: CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, RIGHTS_ISSUE"),
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
):
    """List corporate events with optional filters.

    - month: YYYY-MM format, returns events for that month
    - type: Event type filter (validated against allowed types)
    - symbol: Ticker symbol filter (case-insensitive)
    - No params: returns events from last 90 days to next 90 days
    """
    # T-14-08: Validate event type against allowed set
    if type is not None and type not in ALLOWED_EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type. Must be one of: {', '.join(sorted(ALLOWED_EVENT_TYPES))}",
        )

    # T-14-07: Parse month format strictly
    year_filter: int | None = None
    month_filter: int | None = None
    if month is not None:
        try:
            parts = month.split("-")
            if len(parts) != 2:
                raise ValueError("Expected YYYY-MM")
            year_filter = int(parts[0])
            month_filter = int(parts[1])
            if month_filter < 1 or month_filter > 12:
                raise ValueError("Month must be 1-12")
            if year_filter < 2000 or year_filter > 2100:
                raise ValueError("Year out of range")
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=400,
                detail="Invalid month format. Expected YYYY-MM (e.g., 2026-04)",
            )

    async with async_session() as session:
        # Join CorporateEvent with Ticker to get symbol and name
        stmt = (
            select(
                CorporateEvent.id,
                Ticker.symbol,
                Ticker.name,
                CorporateEvent.event_type,
                CorporateEvent.ex_date,
                CorporateEvent.record_date,
                CorporateEvent.announcement_date,
                CorporateEvent.dividend_amount,
                CorporateEvent.ratio,
                CorporateEvent.note,
            )
            .join(Ticker, CorporateEvent.ticker_id == Ticker.id)
        )

        conditions = []

        # Date filtering
        if year_filter is not None and month_filter is not None:
            # T-14-07: Use extract() — not string concat — for SQL date filtering
            conditions.append(extract("year", CorporateEvent.ex_date) == year_filter)
            conditions.append(extract("month", CorporateEvent.ex_date) == month_filter)
        else:
            # Default: last 90 days to next 90 days
            today = date.today()
            date_start = today - timedelta(days=90)
            date_end = today + timedelta(days=90)
            conditions.append(CorporateEvent.ex_date >= date_start)
            conditions.append(CorporateEvent.ex_date <= date_end)

        # Event type filter
        if type is not None:
            conditions.append(CorporateEvent.event_type == type)

        # Symbol filter (case-insensitive)
        if symbol is not None:
            conditions.append(Ticker.symbol == symbol.upper())

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # T-14-09: Order and limit
        stmt = stmt.order_by(CorporateEvent.ex_date.desc()).limit(500)

        result = await session.execute(stmt)
        rows = result.all()

    return [
        CorporateEventResponse(
            id=row.id,
            symbol=row.symbol,
            name=row.name,
            event_type=row.event_type,
            ex_date=row.ex_date.isoformat(),
            record_date=row.record_date.isoformat() if row.record_date else None,
            announcement_date=row.announcement_date.isoformat() if row.announcement_date else None,
            dividend_amount=float(row.dividend_amount) if row.dividend_amount is not None else None,
            ratio=float(row.ratio) if row.ratio is not None else None,
            note=row.note,
        )
        for row in rows
    ]
