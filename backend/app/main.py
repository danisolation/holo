"""Holo - Stock Intelligence Platform

FastAPI application with APScheduler for automated stock data crawling.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    await telegram_bot.start()
    yield
    # Shutdown
    await telegram_bot.stop()
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


@app.get("/")
async def root():
    return {"status": "ok", "service": "holo"}
