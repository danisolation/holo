"""Goals, weekly prompts, and weekly reviews API endpoints.

POST /goals — set or replace monthly profit target
GET /goals/current — current month goal with computed progress
GET /goals/history — past goals paginated (sorted by month DESC, T-47-03)
GET /goals/weekly-prompt — current pending risk tolerance prompt
POST /goals/weekly-prompt/{prompt_id}/respond — answer weekly prompt
GET /goals/weekly-review — latest AI-generated weekly review
GET /goals/weekly-reviews — review history paginated
"""
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query

from app.database import async_session
from app.services.goal_service import GoalService
from app.schemas.goals import (
    GoalCreate,
    GoalResponse,
    GoalHistoryResponse,
    WeeklyPromptResponse,
    WeeklyPromptRespondRequest,
    WeeklyReviewResponse,
    WeeklyReviewHistoryResponse,
)

router = APIRouter(prefix="/goals", tags=["goals"])

# In-memory cache for weekly review — 300s TTL, only 1 result (latest review)
_weekly_review_cache: TTLCache = TTLCache(maxsize=1, ttl=300)


@router.post("", status_code=201, response_model=GoalResponse)
async def set_goal(data: GoalCreate):
    """Set or replace monthly profit target.

    Per GOAL-01. Pydantic validates target_pnl > 0, le 1B (T-47-01).
    Only 1 active goal per month — replaces existing if found.
    """
    async with async_session() as session:
        service = GoalService(session)
        goal = await service.set_goal(data.target_pnl)
        await session.commit()
        return GoalResponse(
            id=goal.id,
            target_pnl=float(goal.target_pnl),
            actual_pnl=0,
            month=goal.month,
            status=goal.status,
            progress_pct=0,
            progress_color="red",
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )


@router.get("/current", response_model=GoalResponse | None)
async def get_current_goal():
    """Get current month's goal with computed actual_pnl and progress.

    Per GOAL-01. Returns None (null JSON) if no active goal — frontend shows empty state.
    """
    async with async_session() as session:
        service = GoalService(session)
        result = await service.get_current_goal()
        if result is None:
            return None
        return GoalResponse(**result)


@router.get("/history", response_model=GoalHistoryResponse)
async def get_goal_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """Get past goals paginated, sorted by month DESC.

    Per GOAL-01. T-47-03 mitigation: no user-controlled sort — always month DESC.
    """
    async with async_session() as session:
        service = GoalService(session)
        result = await service.get_goal_history(page=page, page_size=page_size)
        return GoalHistoryResponse(**result)


@router.get("/weekly-prompt", response_model=WeeklyPromptResponse | None)
async def get_weekly_prompt():
    """Get current pending weekly risk tolerance prompt.

    Per GOAL-02. Returns None if no pending prompt.
    """
    async with async_session() as session:
        service = GoalService(session)
        prompt = await service.get_pending_prompt()
        if prompt is None:
            return None
        return WeeklyPromptResponse(
            id=prompt.id,
            week_start=prompt.week_start,
            prompt_type=prompt.prompt_type or "risk_tolerance",
            response=prompt.response,
            risk_level_before=prompt.risk_level_before,
            risk_level_after=prompt.risk_level_after,
            created_at=prompt.created_at,
        )


@router.post("/weekly-prompt/{prompt_id}/respond", response_model=WeeklyPromptResponse)
async def respond_to_weekly_prompt(
    prompt_id: int,
    data: WeeklyPromptRespondRequest,
):
    """Record user's weekly prompt response and update risk level.

    Per GOAL-02. T-47-02 mitigation: response validated by Pydantic
    Literal["cautious","unchanged","aggressive"].
    Raises 404 if prompt not found, 400 if already answered.
    """
    async with async_session() as session:
        service = GoalService(session)
        try:
            prompt = await service.respond_to_prompt(prompt_id, data.response)
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            if "already answered" in error_msg:
                raise HTTPException(status_code=400, detail=error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        await session.commit()
        return WeeklyPromptResponse(
            id=prompt.id,
            week_start=prompt.week_start,
            prompt_type=prompt.prompt_type or "risk_tolerance",
            response=prompt.response,
            risk_level_before=prompt.risk_level_before,
            risk_level_after=prompt.risk_level_after,
            created_at=prompt.created_at,
        )


@router.get("/weekly-review", response_model=WeeklyReviewResponse | None)
async def get_weekly_review():
    """Get latest AI-generated weekly performance review.

    Per GOAL-03. Returns None if no reviews exist yet.
    """
    cache_key = "latest"
    cached = _weekly_review_cache.get(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        service = GoalService(session)
        review = await service.get_latest_review()
        if review is None:
            return None
        result = WeeklyReviewResponse(
            id=review.id,
            week_start=review.week_start,
            week_end=review.week_end,
            summary_text=review.summary_text,
            highlights=review.highlights or {"good": [], "bad": []},
            suggestions=review.suggestions or [],
            trades_count=review.trades_count,
            win_count=review.win_count,
            total_pnl=float(review.total_pnl) if review.total_pnl else 0,
            created_at=review.created_at,
        )

    _weekly_review_cache[cache_key] = result
    return result


@router.get("/weekly-reviews", response_model=WeeklyReviewHistoryResponse)
async def get_weekly_review_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """Get weekly review history paginated.

    Per GOAL-03.
    """
    async with async_session() as session:
        service = GoalService(session)
        result = await service.get_review_history(page=page, page_size=page_size)
        reviews = [
            WeeklyReviewResponse(
                id=r.id,
                week_start=r.week_start,
                week_end=r.week_end,
                summary_text=r.summary_text,
                highlights=r.highlights or {"good": [], "bad": []},
                suggestions=r.suggestions or [],
                trades_count=r.trades_count,
                win_count=r.win_count,
                total_pnl=float(r.total_pnl) if r.total_pnl else 0,
                created_at=r.created_at,
            )
            for r in result["reviews"]
        ]
        return WeeklyReviewHistoryResponse(reviews=reviews, total=result["total"])
