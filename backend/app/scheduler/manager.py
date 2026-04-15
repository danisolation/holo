"""APScheduler configuration and lifecycle management.

Uses AsyncIOScheduler (APScheduler 3.11) embedded in FastAPI process.
No external broker needed — jobs run in-process.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import settings

# Single scheduler instance — shared across the application
scheduler = AsyncIOScheduler(timezone=settings.timezone)


def configure_jobs():
    """Register all scheduled jobs. Called once during app startup."""
    from app.scheduler.jobs import (
        daily_price_crawl,
        weekly_ticker_refresh,
        weekly_financial_crawl,
    )

    # Daily OHLCV crawl at 15:30 UTC+7 (45 min after market close)
    # Decision: 15:30 to allow VNDirect time to finalize EOD data
    scheduler.add_job(
        daily_price_crawl,
        trigger=CronTrigger(
            hour=settings.daily_crawl_hour,
            minute=settings.daily_crawl_minute,
            day_of_week="mon-fri",
            timezone=settings.timezone,
        ),
        id="daily_price_crawl",
        name="Daily OHLCV Price Crawl",
        replace_existing=True,
        misfire_grace_time=3600,  # 1 hour grace for missed jobs
    )

    # Weekly ticker list refresh — Sunday 10:00 AM
    # Decision: Refresh weekly to catch IPOs/delistings
    scheduler.add_job(
        weekly_ticker_refresh,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=10,
            minute=0,
            timezone=settings.timezone,
        ),
        id="weekly_ticker_refresh",
        name="Weekly Ticker List Refresh",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    # Weekly financial data crawl — Saturday 08:00 AM
    # Runs on weekends to avoid competing with daily price crawl
    scheduler.add_job(
        weekly_financial_crawl,
        trigger=CronTrigger(
            day_of_week="sat",
            hour=8,
            minute=0,
            timezone=settings.timezone,
        ),
        id="weekly_financial_crawl",
        name="Weekly Financial Data Crawl",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    logger.info(
        f"Scheduled jobs: daily_price_crawl (Mon-Fri {settings.daily_crawl_hour}:{settings.daily_crawl_minute:02d} {settings.timezone}), "
        f"weekly_ticker_refresh (Sun 10:00), weekly_financial_crawl (Sat 08:00)"
    )
