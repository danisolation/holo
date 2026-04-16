"""Holo - Stock Intelligence Platform

FastAPI application with APScheduler for automated stock data crawling.
"""
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.database import engine
from app.scheduler.manager import scheduler, configure_jobs
from app.api.router import api_router
from app.telegram.bot import telegram_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: start scheduler and Telegram bot on startup, clean up on shutdown."""
    # Startup
    logger.info("Holo starting up...")
    configure_jobs()
    scheduler.start()
    logger.info("Scheduler started with configured jobs")
    try:
        await telegram_bot.start()
    except Exception as e:
        logger.warning(f"Telegram bot failed to start (continuing without it): {e}")
    yield
    # Shutdown
    try:
        await telegram_bot.stop()
    except Exception:
        pass
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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")


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
