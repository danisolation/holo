"""API endpoints for AI accuracy tracking (Phase 65)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.accuracy_tracking_service import AccuracyTrackingService

router = APIRouter(prefix="/api/accuracy", tags=["accuracy"])


@router.get("/stats")
async def get_accuracy_stats(
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db),
):
    """Get overall AI prediction accuracy statistics."""
    service = AccuracyTrackingService(db)
    return await service.get_accuracy_stats(days=days)


@router.get("/ticker/{ticker_id}")
async def get_ticker_accuracy(
    ticker_id: int,
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get accuracy stats for a specific ticker."""
    service = AccuracyTrackingService(db)
    return await service.get_ticker_accuracy(ticker_id=ticker_id, days=days)
