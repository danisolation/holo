"""System endpoints: health check, scheduler status, manual crawl triggers.

These endpoints provide operational visibility and manual control over
the data pipeline. In production, the scheduler handles everything
automatically. Manual triggers are for initial setup and debugging.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

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


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def scheduler_status():
    """Get scheduler status and next run times for all jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        jobs.append(JobInfo(id=job.id, name=job.name, next_run=next_run))

    return SchedulerStatusResponse(running=scheduler.running, jobs=jobs)


@router.post("/crawl/daily", response_model=CrawlResultResponse)
async def trigger_daily_crawl(background_tasks: BackgroundTasks):
    """Manually trigger daily OHLCV crawl (runs in background)."""
    async def _run():
        async with async_session() as session:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            result = await service.crawl_daily()
            logger.info(f"Manual daily crawl complete: {result}")

    background_tasks.add_task(_run)
    return CrawlResultResponse(
        message="Daily crawl triggered in background", triggered=True
    )


@router.post("/crawl/tickers", response_model=CrawlResultResponse)
async def trigger_ticker_sync(background_tasks: BackgroundTasks):
    """Manually trigger ticker list sync (runs in background)."""
    async def _run():
        async with async_session() as session:
            crawler = VnstockCrawler()
            service = TickerService(session, crawler)
            result = await service.fetch_and_sync_tickers()
            logger.info(f"Manual ticker sync complete: {result}")

    background_tasks.add_task(_run)
    return CrawlResultResponse(
        message="Ticker sync triggered in background", triggered=True
    )


@router.post("/crawl/financials", response_model=CrawlResultResponse)
async def trigger_financial_crawl(background_tasks: BackgroundTasks):
    """Manually trigger financial data crawl (runs in background)."""
    async def _run():
        async with async_session() as session:
            crawler = VnstockCrawler()
            service = FinancialService(session, crawler)
            result = await service.crawl_financials(period="quarter")
            logger.info(f"Manual financial crawl complete: {result}")

    background_tasks.add_task(_run)
    return CrawlResultResponse(
        message="Financial crawl triggered in background", triggered=True
    )


@router.post("/backfill", response_model=BackfillResultResponse)
async def trigger_backfill(
    start_date: str | None = None,
    end_date: str | None = None,
    background_tasks: BackgroundTasks = None,
):
    """Trigger historical data backfill (runs in background).

    Args:
        start_date: ISO date string, defaults to 2023-07-01
        end_date: ISO date string, defaults to today

    WARNING: This crawls 1-2 years of data for 400 tickers.
    Takes ~13 minutes. Run once on initial setup.
    """
    async def _run():
        async with async_session() as session:
            # Step 1: Ensure tickers are synced first
            crawler = VnstockCrawler()
            ticker_service = TickerService(session, crawler)
            ticker_result = await ticker_service.fetch_and_sync_tickers()
            logger.info(f"Backfill: Ticker sync first — {ticker_result}")

            # Step 2: Backfill prices
            price_service = PriceService(session, crawler)
            price_result = await price_service.backfill(
                start_date=start_date, end_date=end_date
            )
            logger.info(f"Backfill: Price backfill complete — {price_result}")

            # Step 3: Crawl financials
            financial_service = FinancialService(session, crawler)
            financial_result = await financial_service.crawl_financials(period="quarter")
            logger.info(f"Backfill: Financial crawl complete — {financial_result}")

    background_tasks.add_task(_run)
    return BackfillResultResponse(
        message="Backfill triggered in background (tickers → prices → financials). Check logs for progress.",
        triggered=True,
    )
