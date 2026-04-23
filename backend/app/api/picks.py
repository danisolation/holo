"""Daily picks and user profile API endpoints."""
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.database import async_session
from app.services.pick_service import PickService
from app.schemas.picks import (
    DailyPicksResponse,
    PickHistoryListResponse,
    PickPerformanceResponse,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter(tags=["picks"])

# Valid outcome status values for filtering
_VALID_STATUSES = {"all", "winner", "loser", "expired", "pending"}


@router.get("/picks/today", response_model=DailyPicksResponse)
async def get_today_picks():
    """Get today's daily picks with position sizing based on current profile."""
    async with async_session() as session:
        service = PickService(session)
        profile = await service.get_or_create_profile()
        result = await service.get_today_picks(capital=int(profile.capital))
        return result


@router.get("/picks/history", response_model=PickHistoryListResponse)
async def get_pick_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    status: str = Query(default="all", description="Filter by outcome status"),
):
    """Get paginated pick history with outcome data."""
    if status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )
    async with async_session() as session:
        service = PickService(session)
        result = await service.get_pick_history(page=page, per_page=per_page, status=status)
        return result


@router.get("/picks/performance", response_model=PickPerformanceResponse)
async def get_pick_performance():
    """Get aggregated performance stats for performance cards."""
    async with async_session() as session:
        service = PickService(session)
        result = await service.get_performance_stats()
        return result


@router.get("/profile", response_model=ProfileResponse)
async def get_profile():
    """Get current user risk profile."""
    async with async_session() as session:
        service = PickService(session)
        profile = await service.get_or_create_profile()
        return ProfileResponse(
            capital=int(profile.capital),
            risk_level=profile.risk_level,
            broker_fee_pct=float(profile.broker_fee_pct),
        )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(data: ProfileUpdate):
    """Update user risk profile (capital + risk level)."""
    async with async_session() as session:
        service = PickService(session)
        profile = await service.update_profile(
            capital=data.capital,
            risk_level=data.risk_level,
        )
        return ProfileResponse(
            capital=int(profile.capital),
            risk_level=profile.risk_level,
            broker_fee_pct=float(profile.broker_fee_pct),
        )
