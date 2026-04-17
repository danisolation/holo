"""APScheduler configuration and lifecycle management.

Uses AsyncIOScheduler (APScheduler 3.11) embedded in FastAPI process.
No external broker needed — jobs run in-process.
"""
import asyncio

from apscheduler import events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import settings
from app.telegram.formatter import MessageFormatter

# Single scheduler instance — shared across the application
scheduler = AsyncIOScheduler(timezone=settings.timezone)

# Job ID → human-readable name mapping
_JOB_NAMES = {
    "daily_price_crawl": "Daily Price Crawl",
    "weekly_ticker_refresh": "Weekly Ticker Refresh",
    "weekly_financial_crawl": "Weekly Financial Crawl",
    "daily_indicator_compute_triggered": "Daily Indicator Compute",
    "daily_indicator_compute_manual": "Daily Indicator Compute",
    "daily_ai_analysis_triggered": "Daily AI Analysis",
    "daily_ai_analysis_manual": "Daily AI Analysis",
    "daily_news_crawl_triggered": "Daily News Crawl",
    "daily_news_crawl_manual": "Daily News Crawl",
    "daily_sentiment_triggered": "Daily Sentiment Analysis",
    "daily_sentiment_manual": "Daily Sentiment Analysis",
    "daily_combined_triggered": "Daily Combined Analysis",
    "daily_combined_manual": "Daily Combined Analysis",
    "daily_signal_alert_check_triggered": "Daily Signal Alert Check",
    "daily_corporate_action_check_triggered": "Daily Corporate Action Check",
    "daily_price_alert_check_triggered": "Daily Price Alert Check",
    "daily_summary_send": "Daily Market Summary",
}


def _on_job_error(event: events.JobExecutionEvent):
    """Send Telegram notification on complete job failure (D-10).

    Per D-11: Uses existing bot.send_message() pattern (2-retry, never-raises).
    Per D-10: Only fires on complete failure (EVENT_JOB_ERROR), not partial.
    Also logs the alert content as fallback (Pitfall 5 mitigation).
    """
    from app.telegram.bot import telegram_bot

    job_name = _JOB_NAMES.get(event.job_id, event.job_id.replace("_", " ").title())
    error_msg = str(event.exception)[:200] if event.exception else "Unknown error"
    message = MessageFormatter.job_failure_alert(job_name, error_msg)

    # Log the alert content so it's not lost even if Telegram fails (Pitfall 5)
    logger.error(f"CRITICAL FAILURE ALERT: {job_name} — {error_msg}")

    if telegram_bot.is_configured:
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(telegram_bot.send_message(message))
        except RuntimeError:
            logger.warning("Could not send Telegram alert: no running event loop")


def _on_job_executed(event: events.JobExecutionEvent):
    """Chain jobs: price crawl → indicators → AI analysis.

    Triggered by APScheduler's EVENT_JOB_EXECUTED. Only chains on success
    (event.exception is None). Uses add_job with run_date=None to run immediately.
    """
    if event.exception:
        logger.warning(f"Job {event.job_id} failed with exception, not chaining next job")
        return

    if event.job_id == "daily_price_crawl":
        from app.scheduler.jobs import daily_indicator_compute
        logger.info("Chaining: daily_price_crawl → daily_indicator_compute")
        scheduler.add_job(
            daily_indicator_compute,
            id="daily_indicator_compute_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Also trigger price alert check (parallel branch)
        from app.scheduler.jobs import daily_price_alert_check
        logger.info("Chaining: daily_price_crawl → daily_price_alert_check")
        scheduler.add_job(
            daily_price_alert_check,
            id="daily_price_alert_check_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Also trigger corporate action check (parallel branch)
        from app.scheduler.jobs import daily_corporate_action_check
        logger.info("Chaining: daily_price_crawl → daily_corporate_action_check")
        scheduler.add_job(
            daily_corporate_action_check,
            id="daily_corporate_action_check_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_indicator_compute_triggered", "daily_indicator_compute_manual"):
        from app.scheduler.jobs import daily_ai_analysis
        logger.info("Chaining: daily_indicator_compute → daily_ai_analysis")
        scheduler.add_job(
            daily_ai_analysis,
            id="daily_ai_analysis_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_ai_analysis_triggered", "daily_ai_analysis_manual"):
        from app.scheduler.jobs import daily_news_crawl
        logger.info("Chaining: daily_ai_analysis → daily_news_crawl")
        scheduler.add_job(
            daily_news_crawl,
            id="daily_news_crawl_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_news_crawl_triggered", "daily_news_crawl_manual"):
        from app.scheduler.jobs import daily_sentiment_analysis
        logger.info("Chaining: daily_news_crawl → daily_sentiment_analysis")
        scheduler.add_job(
            daily_sentiment_analysis,
            id="daily_sentiment_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_sentiment_triggered", "daily_sentiment_manual"):
        from app.scheduler.jobs import daily_combined_analysis
        logger.info("Chaining: daily_sentiment → daily_combined_analysis")
        scheduler.add_job(
            daily_combined_analysis,
            id="daily_combined_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_combined_triggered", "daily_combined_manual"):
        from app.scheduler.jobs import daily_signal_alert_check
        logger.info("Chaining: daily_combined → daily_signal_alert_check")
        scheduler.add_job(
            daily_signal_alert_check,
            id="daily_signal_alert_check_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )


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

    # Daily market summary at 16:00 UTC+7 (after full pipeline)
    # Per CONTEXT.md D-2.3: 16:00 allows time for all analysis to complete
    from app.scheduler.jobs import daily_summary_send

    scheduler.add_job(
        daily_summary_send,
        trigger=CronTrigger(
            hour=16,
            minute=0,
            day_of_week="mon-fri",
            timezone=settings.timezone,
        ),
        id="daily_summary_send",
        name="Daily Market Summary via Telegram",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        f"Scheduled jobs: daily_price_crawl (Mon-Fri {settings.daily_crawl_hour}:{settings.daily_crawl_minute:02d} {settings.timezone}), "
        f"weekly_ticker_refresh (Sun 10:00), weekly_financial_crawl (Sat 08:00), "
        f"daily_summary_send (Mon-Fri 16:00 {settings.timezone})"
    )

    # Register job chaining listener (Phase 2 + Phase 4)
    scheduler.add_listener(_on_job_executed, events.EVENT_JOB_EXECUTED)
    # Register failure notification listener (Phase 6 — ERR-05)
    scheduler.add_listener(_on_job_error, events.EVENT_JOB_ERROR)
    logger.info(
        "Job chaining registered: "
        "daily_price_crawl → [indicators → AI → news → sentiment → combined → signal_alerts] + [price_alerts] + [corporate_action_check], "
        "daily_summary_send (cron 16:00)"
    )
    logger.info("Failure notification listener registered for EVENT_JOB_ERROR")
