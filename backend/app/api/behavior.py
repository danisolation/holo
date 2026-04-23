"""Behavior tracking API endpoints.

POST /behavior/event — log viewing/click event
GET /behavior/viewing-stats — top 10 most-viewed tickers
GET /behavior/habits — detected trading habits grouped by type
GET /behavior/sector-preferences — sectors ranked by preference_score
GET /behavior/risk-suggestion — current pending risk suggestion
POST /behavior/risk-suggestion/{suggestion_id}/respond — accept/reject suggestion
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.models.ticker import Ticker
from app.services.behavior_service import BehaviorService
from app.schemas.behavior import (
    BehaviorEventCreate,
    ViewingStatsResponse,
    HabitDetectionsResponse,
    SectorPreferencesResponse,
    RiskSuggestionResponse,
    RiskSuggestionRespondRequest,
)

router = APIRouter(prefix="/behavior", tags=["behavior"])


@router.post("/event", status_code=201)
async def log_behavior_event(data: BehaviorEventCreate):
    """Log a viewing or click event.

    Per BEHV-01: event_type validated by Pydantic regex (T-46-01).
    If ticker_symbol provided, resolves to ticker_id.
    """
    async with async_session() as session:
        # Resolve ticker_symbol → ticker_id if provided
        ticker_id = None
        if data.ticker_symbol:
            result = await session.execute(
                select(Ticker.id).where(Ticker.symbol == data.ticker_symbol.upper())
            )
            ticker_id = result.scalar_one_or_none()
            if ticker_id is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Ticker not found: {data.ticker_symbol}",
                )

        service = BehaviorService(session)
        event_id = await service.log_event(
            event_type=data.event_type,
            ticker_id=ticker_id,
            event_metadata=data.metadata,
        )
        await session.commit()
        return {"id": event_id}


@router.get("/viewing-stats", response_model=ViewingStatsResponse)
async def get_viewing_stats():
    """Return top 10 most-viewed tickers with counts and sectors.

    Per BEHV-01.
    """
    async with async_session() as session:
        service = BehaviorService(session)
        result = await service.get_viewing_stats(limit=10)
        return result


@router.get("/habits", response_model=HabitDetectionsResponse)
async def get_habits():
    """Return detected trading habits grouped by type with counts.

    Per BEHV-02. Reads stored detections — detection happens in weekly batch job.
    """
    async with async_session() as session:
        service = BehaviorService(session)
        result = await service.get_habit_detections()
        return result


@router.get("/sector-preferences", response_model=SectorPreferencesResponse)
async def get_sector_preferences():
    """Return sectors ranked by preference_score with insufficient_count.

    Per ADPT-02.
    """
    async with async_session() as session:
        service = BehaviorService(session)
        result = await service.get_sector_preferences()
        return result


@router.get("/risk-suggestion", response_model=RiskSuggestionResponse | None)
async def get_risk_suggestion():
    """Return current pending risk suggestion or null.

    Per ADPT-01.
    """
    async with async_session() as session:
        service = BehaviorService(session)
        suggestion = await service.get_pending_risk_suggestion()
        if suggestion is None:
            return None
        return RiskSuggestionResponse(
            id=suggestion.id,
            current_level=suggestion.current_level,
            suggested_level=suggestion.suggested_level,
            reason=suggestion.reason,
            status=suggestion.status,
            created_at=suggestion.created_at.isoformat() if suggestion.created_at else "",
        )


@router.post("/risk-suggestion/{suggestion_id}/respond", response_model=RiskSuggestionResponse)
async def respond_to_risk_suggestion(
    suggestion_id: int,
    data: RiskSuggestionRespondRequest,
):
    """Accept or reject a pending risk suggestion.

    Per ADPT-01. T-46-04 mitigation: service validates suggestion exists AND status='pending'.
    T-46-02 mitigation: action validated by Pydantic regex.
    """
    async with async_session() as session:
        service = BehaviorService(session)
        try:
            suggestion = await service.respond_to_risk_suggestion(suggestion_id, data.action)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"No pending risk suggestion found with id={suggestion_id}",
            )
        await session.commit()
        return RiskSuggestionResponse(
            id=suggestion.id,
            current_level=suggestion.current_level,
            suggested_level=suggestion.suggested_level,
            reason=suggestion.reason,
            status=suggestion.status,
            created_at=suggestion.created_at.isoformat() if suggestion.created_at else "",
        )
