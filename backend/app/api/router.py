"""Main API router combining all sub-routers."""
from fastapi import APIRouter

from app.api.system import router as system_router
from app.api.analysis import router as analysis_router
from app.api.tickers import router as tickers_router
from app.api.portfolio import router as portfolio_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(analysis_router)
api_router.include_router(tickers_router)
api_router.include_router(portfolio_router)
