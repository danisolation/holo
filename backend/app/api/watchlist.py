"""Watchlist API endpoints with AI signal enrichment.

CRUD operations for the web watchlist (single-user, no auth).
GET enriches each symbol with latest combined AI signal/score via JOIN.
POST /migrate supports one-time localStorage→DB migration.
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, delete, func as sa_func, and_

from app.database import async_session
from app.models.user_watchlist import UserWatchlist
from app.models.ticker import Ticker
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.schemas.watchlist import (
    WatchlistItemResponse,
    WatchlistAddRequest,
    WatchlistUpdateRequest,
    WatchlistMigrateRequest,
    PaginatedWatchlistResponse,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


async def _get_enriched_watchlist(
    session, page: int = 1, per_page: int = 50
) -> PaginatedWatchlistResponse:
    """Fetch paginated watchlist items enriched with latest combined AI signal.

    JOIN path: UserWatchlist.symbol → Ticker.symbol → Ticker.id → AIAnalysis.ticker_id
    Only the most recent 'combined' analysis per ticker is used.
    """
    # Total count for pagination
    count_result = await session.execute(
        select(sa_func.count()).select_from(UserWatchlist)
    )
    total = count_result.scalar_one()

    # Subquery: latest combined analysis date per ticker
    latest_analysis = (
        select(
            AIAnalysis.ticker_id,
            sa_func.max(AIAnalysis.analysis_date).label("max_date"),
        )
        .where(AIAnalysis.analysis_type == AnalysisType.COMBINED)
        .group_by(AIAnalysis.ticker_id)
        .subquery()
    )

    # Phase 58: Subquery — most recent AI analysis created_at per ticker (any type)
    latest_created = (
        select(
            AIAnalysis.ticker_id,
            sa_func.max(AIAnalysis.created_at).label("max_created_at"),
        )
        .group_by(AIAnalysis.ticker_id)
        .subquery()
    )

    # Main query: watchlist LEFT JOIN ticker LEFT JOIN latest combined analysis
    offset = (page - 1) * per_page
    stmt = (
        select(
            UserWatchlist.symbol,
            UserWatchlist.created_at,
            UserWatchlist.sector_group,
            AIAnalysis.signal,
            AIAnalysis.score,
            AIAnalysis.analysis_date,
            latest_created.c.max_created_at,
        )
        .outerjoin(Ticker, UserWatchlist.symbol == Ticker.symbol)
        .outerjoin(
            latest_analysis,
            Ticker.id == latest_analysis.c.ticker_id,
        )
        .outerjoin(
            AIAnalysis,
            and_(
                AIAnalysis.ticker_id == Ticker.id,
                AIAnalysis.analysis_type == AnalysisType.COMBINED,
                AIAnalysis.analysis_date == latest_analysis.c.max_date,
            ),
        )
        .outerjoin(
            latest_created,
            Ticker.id == latest_created.c.ticker_id,
        )
        .order_by(UserWatchlist.created_at.desc(), UserWatchlist.symbol.asc())
        .offset(offset)
        .limit(per_page)
    )

    result = await session.execute(stmt)
    rows = result.all()

    items = [
        WatchlistItemResponse(
            symbol=row.symbol,
            created_at=row.created_at.isoformat(),
            sector_group=row.sector_group,
            ai_signal=row.signal,
            ai_score=row.score,
            signal_date=row.analysis_date.isoformat() if row.analysis_date else None,
            last_analysis_at=row.max_created_at.isoformat() if row.max_created_at else None,
        )
        for row in rows
    ]

    return PaginatedWatchlistResponse(
        items=items, total=total, page=page, per_page=per_page
    )


@router.get("/", response_model=PaginatedWatchlistResponse)
async def get_watchlist(page: int = 1, per_page: int = 50):
    """Get paginated watchlist items with AI signal enrichment."""
    per_page = min(per_page, 100)
    async with async_session() as session:
        return await _get_enriched_watchlist(session, page=page, per_page=per_page)


@router.post("/", response_model=WatchlistItemResponse, status_code=201)
async def add_to_watchlist(body: WatchlistAddRequest):
    """Add a symbol to the watchlist. Idempotent — returns existing if already present."""
    symbol = body.symbol.upper().strip()

    async with async_session() as session:
        # Check if already exists
        stmt = select(UserWatchlist).where(UserWatchlist.symbol == symbol)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return WatchlistItemResponse(
                symbol=existing.symbol,
                created_at=existing.created_at.isoformat(),
                sector_group=existing.sector_group,
            )

        # Determine sector_group: user-provided > ICB auto-populate > None
        sector = body.sector_group
        if sector is None:
            ticker_stmt = select(Ticker.sector).where(Ticker.symbol == symbol)
            ticker_result = await session.execute(ticker_stmt)
            ticker_row = ticker_result.scalar_one_or_none()
            if ticker_row:
                sector = ticker_row

        # Insert new entry
        entry = UserWatchlist(symbol=symbol, sector_group=sector)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

        return WatchlistItemResponse(
            symbol=entry.symbol,
            created_at=entry.created_at.isoformat(),
            sector_group=entry.sector_group,
        )


@router.patch("/{symbol}", response_model=WatchlistItemResponse)
async def update_watchlist_item(symbol: str, body: WatchlistUpdateRequest):
    """Update sector_group for a watchlist item."""
    symbol = symbol.upper().strip()
    async with async_session() as session:
        stmt = select(UserWatchlist).where(UserWatchlist.symbol == symbol)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail=f"'{symbol}' not in watchlist")
        item.sector_group = body.sector_group
        await session.commit()
        await session.refresh(item)
        return WatchlistItemResponse(
            symbol=item.symbol,
            created_at=item.created_at.isoformat(),
            sector_group=item.sector_group,
        )


@router.delete("/{symbol}", status_code=204)
async def remove_from_watchlist(symbol: str):
    """Remove a symbol from the watchlist. Returns 404 if not found."""
    symbol = symbol.upper().strip()

    async with async_session() as session:
        stmt = delete(UserWatchlist).where(UserWatchlist.symbol == symbol)
        result = await session.execute(stmt)
        await session.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not in watchlist")


@router.post("/migrate", response_model=PaginatedWatchlistResponse)
async def migrate_watchlist(body: WatchlistMigrateRequest):
    """Bulk add symbols from localStorage migration.

    Skips symbols already in watchlist. Returns full enriched list.
    One-time use for localStorage→DB migration on first web dashboard load.
    """
    async with async_session() as session:
        # Get existing symbols
        stmt = select(UserWatchlist.symbol)
        result = await session.execute(stmt)
        existing_symbols = {row[0] for row in result.all()}

        # Insert new symbols
        for raw_symbol in body.symbols:
            symbol = raw_symbol.upper().strip()
            if not symbol or symbol in existing_symbols:
                continue
            entry = UserWatchlist(symbol=symbol)
            session.add(entry)
            existing_symbols.add(symbol)

        await session.commit()

        # Return full enriched watchlist (first page)
        return await _get_enriched_watchlist(session, page=1, per_page=50)
