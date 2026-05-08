"""Holo - Stock Intelligence Platform

FastAPI application with APScheduler for automated stock data crawling.
"""
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.database import engine
from app.scheduler.manager import scheduler, configure_jobs
from app.api.router import api_router
from app.ws.prices import websocket_prices


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: start scheduler on startup, clean up on shutdown."""
    import asyncio

    vndirect_task = None
    vndirect_client = None

    # Startup
    logger.info("Holo starting up...")

    # Auto-seed tickers if DB is empty (first deploy after reset)
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM tickers"))
            ticker_count = result.scalar()
            if ticker_count == 0:
                logger.info("No tickers found — running initial ticker sync...")
                from app.crawlers.vnstock_crawler import VnstockCrawler
                from app.services.ticker_service import TickerService
                crawler = VnstockCrawler()
                svc = TickerService(session, crawler)
                sync_result = await svc.fetch_and_sync_tickers("HOSE")
                await session.commit()
                logger.info(f"Initial ticker sync complete: {sync_result}")
            else:
                logger.info(f"Found {ticker_count} tickers in DB")
    except Exception as e:
        logger.warning(f"Startup ticker check failed (non-fatal): {e}")

    if settings.holo_test_mode:
        logger.info("HOLO_TEST_MODE=true — skipping scheduler")
    else:
        configure_jobs()
        scheduler.start()
        logger.info("Scheduler started with configured jobs")

        # Launch VNDirect WebSocket client if enabled
        if settings.vndirect_ws_enabled:
            from app.services.vndirect_ws_client import VNDirectWSClient
            from app.services.realtime_price_service import get_realtime_price_service
            from app.ws.prices import connection_manager

            realtime_svc = get_realtime_price_service()

            async def _activate_vci_polling_fallback():
                """Start VCI polling when VNDirect WS fails repeatedly."""
                from apscheduler.triggers.interval import IntervalTrigger
                from app.scheduler.jobs import realtime_price_poll, realtime_heartbeat

                if scheduler.get_job("realtime_price_poll"):
                    return  # Already active
                scheduler.add_job(
                    realtime_price_poll,
                    trigger=IntervalTrigger(seconds=settings.realtime_poll_interval),
                    id="realtime_price_poll",
                    name="Real-Time Price Poll (fallback)",
                    replace_existing=True,
                    misfire_grace_time=30,
                )
                scheduler.add_job(
                    realtime_heartbeat,
                    trigger=IntervalTrigger(seconds=15),
                    id="realtime_heartbeat",
                    name="Real-Time Heartbeat (fallback)",
                    replace_existing=True,
                    misfire_grace_time=10,
                )
                logger.info("VCI polling fallback activated")
            # Get watchlist symbols from connection manager subscriptions
            # (populated when frontend connects and subscribes)
            # The WS client will subscribe to all symbols initially;
            # frontend subscription filtering happens at broadcast level
            symbols = list(connection_manager.get_all_subscribed_symbols())
            if not symbols:
                # Default to empty — client will still connect and wait for subscriptions
                # Symbols can be updated dynamically via client.update_symbols()
                symbols = []

            vndirect_client = VNDirectWSClient(
                symbols=symbols,
                on_price_update=realtime_svc.handle_ws_price_update,
                on_bid_ask_update=realtime_svc.handle_ws_bid_ask_update,
                ws_url=settings.vndirect_ws_url,
                on_fallback=_activate_vci_polling_fallback,
            )
            vndirect_task = asyncio.create_task(vndirect_client.start())
            logger.info("VNDirect WebSocket client launched as background task")

            # Store client on app state for dynamic symbol updates
            app.state.vndirect_client = vndirect_client

    yield
    # Shutdown
    if vndirect_client:
        await vndirect_client.stop()
        if vndirect_task:
            vndirect_task.cancel()
        logger.info("VNDirect WebSocket client stopped")
    if not settings.holo_test_mode:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    await engine.dispose()
    logger.info("Database engine disposed. Holo shut down.")


app = FastAPI(
    title="Holo - Stock Intelligence",
    description="AI-powered stock analysis for HOSE",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server + configured origins (Render, etc.)
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "https://holo-jade-six.vercel.app"]
_extra_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Mount API routes
app.include_router(api_router, prefix="/api")

# WebSocket route — real-time price updates (Phase 16)
# Mounted directly on app (not via APIRouter) per FastAPI WebSocket best practice
app.websocket("/ws/prices")(websocket_prices)


# Global exception handler — log tracebacks and return JSON instead of bare 500
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions so they return JSON (not plain text 500).

    Logs full traceback for debugging. Without this, FastAPI/uvicorn returns
    bare 'Internal Server Error' text with no traceback in the response.
    """
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url}:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": str(request.url.path),
        },
    )


@app.get("/")
async def root():
    return {"status": "ok", "service": "holo"}
