"""System endpoints: health check, scheduler status, manual crawl triggers.

These endpoints provide operational visibility and manual control over
the data pipeline. In production, the scheduler handles everything
automatically. Manual triggers are for initial setup and debugging.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.database import get_db, async_session, engine
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.services.price_service import PriceService
from app.services.ticker_service import TickerService
from app.services.financial_service import FinancialService
from app.scheduler.manager import scheduler


router = APIRouter(tags=["system"])


# --- Response Models ---

class HealthResponse(BaseModel):
    status: str
    database: str
    scheduler: str
    timestamp: str


class JobInfo(BaseModel):
    id: str
    name: str
    next_run: str | None


class SchedulerStatusResponse(BaseModel):
    running: bool
    jobs: list[JobInfo]


class CrawlResultResponse(BaseModel):
    message: str
    triggered: bool


class BackfillResultResponse(BaseModel):
    message: str
    triggered: bool


# --- Endpoints ---

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of database connection and scheduler."""
    # Check database
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"

    # Check scheduler
    scheduler_status = "running" if scheduler.running else "stopped"

    overall = "healthy" if db_status == "connected" and scheduler_status == "running" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        scheduler=scheduler_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/config")
async def health_config():
    """Debug: show active config (safe subset)."""
    return {
        "gemini_model": settings.gemini_model,
        "gemini_batch_size": settings.gemini_batch_size,
        "rumor_batch_size": settings.rumor_batch_size,
        "gemini_api_key_set": bool(settings.gemini_api_key),
    }


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def scheduler_status():
    """Get scheduler status and next run times for all jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append(JobInfo(id=job.id, name=job.name, next_run=next_run))

    return SchedulerStatusResponse(running=scheduler.running, jobs=jobs)


@router.post("/crawl/daily")
async def trigger_daily_crawl():
    """Manually trigger daily OHLCV crawl (streaming to keep alive)."""
    async def _stream():
        async with async_session() as session:
            try:
                yield "data: Starting daily crawl...\n\n"
                crawler = VnstockCrawler()
                service = PriceService(session, crawler)
                result = await service.crawl_daily()
                yield f"data: Daily crawl complete: {result}\n\n"
            except Exception as e:
                yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/crawl/tickers")
async def trigger_ticker_sync():
    """Manually trigger ticker list sync (streaming)."""
    async def _stream():
        async with async_session() as session:
            try:
                yield "data: Starting ticker sync...\n\n"
                crawler = VnstockCrawler()
                service = TickerService(session, crawler)
                result = await service.fetch_and_sync_tickers()
                yield f"data: Ticker sync complete: {result}\n\n"
            except Exception as e:
                yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/crawl/financials")
async def trigger_financial_crawl():
    """Manually trigger financial data crawl via CafeF scraping (streaming)."""
    async def _stream():
        async with async_session() as session:
            try:
                yield "data: Starting financial crawl (CafeF)...\n\n"
                from app.crawlers.cafef_financial_crawler import CafeFFinancialCrawler
                crawler = CafeFFinancialCrawler(session)
                result = await crawler.crawl_financials()
                yield f"data: Financial crawl complete: {result}\n\n"
            except Exception as e:
                yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/backfill")
async def trigger_backfill(
    start_date: str | None = None,
    end_date: str | None = None,
    skip_ticker_sync: bool = True,
):
    """Trigger historical data backfill as a streaming response.

    Streams progress line-by-line so the connection stays alive and
    Render free tier doesn't kill the process.
    """
    async def _stream():
        async with async_session() as session:
            try:
                crawler = VnstockCrawler()

                # Step 1: Ticker sync (optional, skip if already seeded)
                if not skip_ticker_sync:
                    yield "data: [1/3] Syncing tickers...\n\n"
                    ticker_service = TickerService(session, crawler)
                    ticker_result = await ticker_service.fetch_and_sync_tickers()
                    yield f"data: [1/3] Ticker sync done: {ticker_result}\n\n"
                else:
                    yield "data: [1/3] Ticker sync skipped (already seeded)\n\n"

                # Step 2: Backfill prices
                yield "data: [2/3] Starting price backfill...\n\n"
                price_service = PriceService(session, crawler)
                price_result = await price_service.backfill(
                    start_date=start_date, end_date=end_date
                )
                yield f"data: [2/3] Price backfill done: {price_result}\n\n"

                # Step 3: Crawl financials via CafeF
                yield "data: [3/3] Starting financial crawl...\n\n"
                from app.crawlers.cafef_financial_crawler import CafeFFinancialCrawler
                cafef_crawler = CafeFFinancialCrawler(session)
                financial_result = await cafef_crawler.crawl_financials()
                yield f"data: [3/3] Financial crawl done: {financial_result}\n\n"

                yield "data: [COMPLETE] All backfill steps finished successfully.\n\n"
            except Exception as e:
                logger.error(f"Backfill failed: {e}")
                yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
