"""Main API router combining all sub-routers."""
from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.analysis import router as analysis_router
from app.api.tickers import router as tickers_router
from app.api.health import router as health_router
from app.api.picks import router as picks_router
from app.api.trades import router as trades_router
from app.api.behavior import router as behavior_router
from app.api.goals import router as goals_router
from app.api.watchlist import router as watchlist_router
from app.api.discovery import router as discovery_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(analysis_router)
api_router.include_router(tickers_router)
api_router.include_router(health_router)
api_router.include_router(picks_router)
api_router.include_router(trades_router)
api_router.include_router(behavior_router)
api_router.include_router(goals_router)
api_router.include_router(watchlist_router)
api_router.include_router(discovery_router)
