"""Rumor intelligence API: scores and posts for tickers."""
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.ticker import Ticker
from app.models.rumor import Rumor
from app.models.rumor_score import RumorScore
from app.models.user_watchlist import UserWatchlist
from app.schemas.rumor import (
    RumorScoreResponse,
    RumorPostResponse,
    WatchlistRumorSummary,
)

router = APIRouter(prefix="/rumors", tags=["rumors"])


# --- Helpers ---

async def _get_ticker_by_symbol(session: AsyncSession, symbol: str) -> Ticker:
    """Resolve ticker symbol to Ticker object. Raises 404 if not found."""
    result = await session.execute(
        select(Ticker).where(Ticker.symbol == symbol.upper())
    )
    ticker = result.scalar_one_or_none()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker '{symbol}' not found")
    return ticker


# --- Endpoints ---
# NOTE: /watchlist/summary MUST be defined BEFORE /{symbol}
# otherwise FastAPI treats "watchlist" as a {symbol} parameter.


@router.get("/watchlist/summary", response_model=list[WatchlistRumorSummary])
async def get_watchlist_rumor_summary():
    """Get rumor badge data for all watchlist tickers (last 7 days).

    Returns aggregated rumor counts, average scores, and dominant direction
    for each ticker in the user's watchlist.
    """
    seven_days_ago = date.today() - timedelta(days=7)

    async with async_session() as session:
        # Get all watchlist symbols with their ticker IDs
        wl_stmt = (
            select(UserWatchlist.symbol, Ticker.id.label("ticker_id"))
            .outerjoin(Ticker, UserWatchlist.symbol == Ticker.symbol)
        )
        wl_result = await session.execute(wl_stmt)
        watchlist_items = wl_result.all()

        # Collect valid ticker IDs from watchlist
        ticker_ids = [item.ticker_id for item in watchlist_items if item.ticker_id is not None]

        # Batch Query A: Rumor counts per ticker (last 7 days)
        counts: dict[int, int] = {}
        if ticker_ids:
            count_result = await session.execute(
                select(
                    Rumor.ticker_id,
                    func.count(Rumor.id).label("rumor_count"),
                )
                .where(
                    Rumor.ticker_id.in_(ticker_ids),
                    Rumor.posted_at >= seven_days_ago,
                )
                .group_by(Rumor.ticker_id)
            )
            counts = {row.ticker_id: row.rumor_count for row in count_result.all()}

        # Batch Query B: Score aggregates per ticker (last 7 days)
        scores: dict[int, tuple] = {}
        if ticker_ids:
            score_result = await session.execute(
                select(
                    RumorScore.ticker_id,
                    func.avg(RumorScore.credibility_score).label("avg_cred"),
                    func.avg(RumorScore.impact_score).label("avg_impact"),
                )
                .where(
                    RumorScore.ticker_id.in_(ticker_ids),
                    RumorScore.scored_date >= seven_days_ago,
                )
                .group_by(RumorScore.ticker_id)
            )
            scores = {
                row.ticker_id: (
                    round(float(row.avg_cred), 1) if row.avg_cred else None,
                    round(float(row.avg_impact), 1) if row.avg_impact else None,
                )
                for row in score_result.all()
            }

        # Batch Query C: Dominant direction per ticker (last 7 days)
        directions: dict[int, str] = {}
        if ticker_ids:
            dir_subq = (
                select(
                    RumorScore.ticker_id,
                    RumorScore.direction,
                    func.count(RumorScore.id).label("cnt"),
                )
                .where(
                    RumorScore.ticker_id.in_(ticker_ids),
                    RumorScore.scored_date >= seven_days_ago,
                )
                .group_by(RumorScore.ticker_id, RumorScore.direction)
                .subquery()
            )
            dir_stmt = (
                select(
                    dir_subq.c.ticker_id,
                    dir_subq.c.direction,
                )
                .distinct(dir_subq.c.ticker_id)
                .order_by(dir_subq.c.ticker_id, dir_subq.c.cnt.desc())
            )
            dir_result = await session.execute(dir_stmt)
            directions = {row.ticker_id: row.direction for row in dir_result.all()}

        # Assemble summaries from lookup dicts
        summaries = []
        for item in watchlist_items:
            if item.ticker_id is None:
                summaries.append(WatchlistRumorSummary(
                    symbol=item.symbol,
                    rumor_count=0,
                ))
                continue

            tid = item.ticker_id
            score_tuple = scores.get(tid, (None, None))
            summaries.append(WatchlistRumorSummary(
                symbol=item.symbol,
                rumor_count=counts.get(tid, 0),
                avg_credibility=score_tuple[0],
                avg_impact=score_tuple[1],
                dominant_direction=directions.get(tid),
            ))

        return summaries


@router.get("/{symbol}", response_model=RumorScoreResponse)
async def get_ticker_rumors(symbol: str):
    """Get latest rumor score and recent posts for a ticker.

    Returns score fields from the most recent RumorScore (or None if no score),
    and the 20 most recent Rumor posts for the feed.
    If ticker exists but has no rumor data, returns empty response (not 404).
    """
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)

        # Latest score
        score_result = await session.execute(
            select(RumorScore)
            .where(RumorScore.ticker_id == ticker.id)
            .order_by(RumorScore.scored_date.desc())
            .limit(1)
        )
        latest_score = score_result.scalar_one_or_none()

        # Recent posts (limit 20)
        posts_result = await session.execute(
            select(Rumor)
            .where(Rumor.ticker_id == ticker.id)
            .order_by(Rumor.posted_at.desc())
            .limit(20)
        )
        posts = posts_result.scalars().all()

        return RumorScoreResponse(
            symbol=ticker.symbol,
            scored_date=latest_score.scored_date.isoformat() if latest_score else None,
            credibility_score=latest_score.credibility_score if latest_score else None,
            impact_score=latest_score.impact_score if latest_score else None,
            direction=latest_score.direction if latest_score else None,
            key_claims=latest_score.key_claims if latest_score else [],
            reasoning=latest_score.reasoning if latest_score else None,
            posts=[
                RumorPostResponse(
                    content=post.content,
                    author_name=post.author_name,
                    is_authentic=post.is_authentic,
                    total_likes=post.total_likes,
                    total_replies=post.total_replies,
                    posted_at=post.posted_at.isoformat(),
                )
                for post in posts
            ],
        )
