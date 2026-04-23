"""Main API router combining all sub-routers."""
from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.analysis import router as analysis_router
from app.api.tickers import router as tickers_router
from app.api.health import router as health_router
from app.api.corporate_events import router as corporate_events_router
from app.api.picks import router as picks_router
from app.api.trades import router as trades_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(analysis_router)
api_router.include_router(tickers_router)
api_router.include_router(health_router)
api_router.include_router(corporate_events_router)
api_router.include_router(picks_router)
api_router.include_router(trades_router)
