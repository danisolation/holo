"""Daily picks and user profile API endpoints."""
from datetime import date

from fastapi import APIRouter
from loguru import logger

from app.database import async_session
from app.services.pick_service import PickService
from app.schemas.picks import DailyPicksResponse, ProfileResponse, ProfileUpdate

router = APIRouter(tags=["picks"])


@router.get("/picks/today", response_model=DailyPicksResponse)
async def get_today_picks():
    """Get today's daily picks with position sizing based on current profile."""
    async with async_session() as session:
        service = PickService(session)
        profile = await service.get_or_create_profile()
        result = await service.get_today_picks(capital=int(profile.capital))
        return result


@router.get("/picks/history")
async def get_pick_history(days: int = 30):
    """Get pick history for the last N days. Placeholder for Phase 45."""
    async with async_session() as session:
        service = PickService(session)
        result = await service.get_pick_history(days=days)
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
