"""APScheduler configuration and lifecycle management.

Uses AsyncIOScheduler (APScheduler 3.11) embedded in FastAPI process.
No external broker needed — jobs run in-process.
"""

from apscheduler import events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.config import settings

# Single scheduler instance — shared across the application
scheduler = AsyncIOScheduler(timezone=settings.timezone)

# Job ID → human-readable name mapping
_JOB_NAMES = {
    "daily_price_crawl": "Daily Price Crawl",
    "daily_price_crawl_hose": "Daily Price Crawl (HOSE)",
    "daily_price_crawl_hnx": "Daily Price Crawl (HNX)",
    "daily_price_crawl_upcom": "Daily Price Crawl (UPCOM)",
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
    "daily_trading_signal_triggered": "Daily Trading Signal Analysis",
    "daily_trading_signal_manual": "Daily Trading Signal Analysis",
    "daily_corporate_action_check_triggered": "Daily Corporate Action Check",
    "daily_hnx_upcom_analysis": "Daily HNX/UPCOM Watchlist Analysis",
    "daily_hnx_upcom_analysis_triggered": "Daily HNX/UPCOM Watchlist Analysis",
    "daily_pick_generation_triggered": "Daily Pick Generation",
    "daily_pick_generation_manual": "Daily Pick Generation",
    "daily_pick_outcome_check_triggered": "Daily Pick Outcome Check",
    "daily_pick_outcome_check_manual": "Daily Pick Outcome Check",
    "weekly_behavior_analysis": "Weekly Behavior Analysis",
    "daily_consecutive_loss_check": "Daily Consecutive Loss Check",
    "daily_consecutive_loss_check_triggered": "Daily Consecutive Loss Check",
    "create_weekly_risk_prompt": "Weekly Risk Tolerance Prompt",
    "generate_weekly_review": "AI Weekly Performance Review",
    "generate_weekly_review_triggered": "AI Weekly Performance Review",
    "realtime_price_poll": "Real-Time Price Poll",
    "realtime_heartbeat": "Real-Time Heartbeat",
}


def _on_job_error(event: events.JobExecutionEvent):
    """Log complete job failure (formerly sent Telegram notification)."""
    job_name = _JOB_NAMES.get(event.job_id, event.job_id.replace("_", " ").title())
    error_msg = str(event.exception)[:200] if event.exception else "Unknown error"
    logger.error(f"CRITICAL FAILURE ALERT: {job_name} — {error_msg}")


def _on_job_executed(event: events.JobExecutionEvent):
    """Chain jobs: price crawl → indicators → AI analysis.

    Triggered by APScheduler's EVENT_JOB_EXECUTED. Only chains on success
    (event.exception is None). Uses add_job with run_date=None to run immediately.
    """
    if event.exception:
        logger.warning(f"Job {event.job_id} failed with exception, not chaining next job")
        return

    if event.job_id == "daily_price_crawl_upcom":
        from app.scheduler.jobs import daily_indicator_compute
        logger.info("Chaining: daily_price_crawl_upcom → daily_indicator_compute")
        scheduler.add_job(
            daily_indicator_compute,
            id="daily_indicator_compute_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Also trigger corporate action check (parallel branch)
        from app.scheduler.jobs import daily_corporate_action_check
        logger.info("Chaining: daily_price_crawl_upcom → daily_corporate_action_check")
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
        # Phase 19: Chain to trading signal analysis (NOT directly to alerts)
        from app.scheduler.jobs import daily_trading_signal_analysis
        logger.info("Chaining: daily_combined → daily_trading_signal_analysis")
        scheduler.add_job(
            daily_trading_signal_analysis,
            id="daily_trading_signal_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_trading_signal_triggered",):
        # Chain HNX/UPCOM watchlist analysis
        from app.scheduler.jobs import daily_hnx_upcom_analysis
        logger.info("Chaining: daily_trading_signal → daily_hnx_upcom_analysis")
        scheduler.add_job(
            daily_hnx_upcom_analysis,
            id="daily_hnx_upcom_analysis_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_hnx_upcom_analysis_triggered",):
        # Phase 43: Chain daily pick generation (last step in pipeline)
        from app.scheduler.jobs import daily_pick_generation
        logger.info("Chaining: daily_hnx_upcom_analysis → daily_pick_generation")
        scheduler.add_job(
            daily_pick_generation,
            id="daily_pick_generation_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_pick_generation_triggered", "daily_pick_generation_manual"):
        # Phase 45: Chain daily pick outcome check after pick generation
        from app.scheduler.jobs import daily_pick_outcome_check
        logger.info("Chaining: daily_pick_generation → daily_pick_outcome_check")
        scheduler.add_job(
            daily_pick_outcome_check,
            id="daily_pick_outcome_check_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_pick_outcome_check_triggered", "daily_pick_outcome_check_manual"):
        # Phase 46: Chain consecutive loss check after pick outcome check
        from app.scheduler.jobs import daily_consecutive_loss_check
        logger.info("Chaining: daily_pick_outcome_check → daily_consecutive_loss_check")
        scheduler.add_job(
            daily_consecutive_loss_check,
            id="daily_consecutive_loss_check_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id == "weekly_behavior_analysis":
        # Phase 47: Chain weekly review generation after behavior analysis
        from app.scheduler.jobs import generate_weekly_review
        logger.info("Chaining: weekly_behavior_analysis → generate_weekly_review")
        scheduler.add_job(
            generate_weekly_review,
            id="generate_weekly_review_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )


def configure_jobs():
    """Register all scheduled jobs. Called once during app startup."""
    import functools
    from app.scheduler.jobs import (
        daily_price_crawl_for_exchange,
        weekly_ticker_refresh,
        weekly_financial_crawl,
    )

    # Staggered exchange crawls: HOSE 15:30, HNX 16:00, UPCOM 16:30
    # Chain only triggers from UPCOM (the last exchange crawl)
    EXCHANGE_CRAWL_SCHEDULE = {
        "HOSE":  {"hour": 15, "minute": 30},
        "HNX":   {"hour": 16, "minute": 0},
        "UPCOM": {"hour": 16, "minute": 30},
    }

    for exchange, schedule in EXCHANGE_CRAWL_SCHEDULE.items():
        scheduler.add_job(
            functools.partial(daily_price_crawl_for_exchange, exchange),
            trigger=CronTrigger(
                hour=schedule["hour"],
                minute=schedule["minute"],
                day_of_week="mon-fri",
                timezone=settings.timezone,
            ),
            id=f"daily_price_crawl_{exchange.lower()}",
            name=f"Daily OHLCV Price Crawl ({exchange})",
            replace_existing=True,
            misfire_grace_time=3600,
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
        f"Scheduled jobs: daily_price_crawl_hose (Mon-Fri 15:30 {settings.timezone}), "
        f"daily_price_crawl_hnx (Mon-Fri 16:00), daily_price_crawl_upcom (Mon-Fri 16:30), "
        f"weekly_ticker_refresh (Sun 10:00), weekly_financial_crawl (Sat 08:00)"
    )

    # ── Phase 46: Weekly behavior analysis (Sunday 20:00) ─────────────────
    from app.scheduler.jobs import weekly_behavior_analysis

    scheduler.add_job(
        weekly_behavior_analysis,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=20,
            minute=0,
            timezone=settings.timezone,
        ),
        id="weekly_behavior_analysis",
        name="Weekly Behavior Analysis",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    logger.info("Behavior jobs: weekly_behavior_analysis (Sun 20:00), daily_consecutive_loss_check (chained)")

    # ── Phase 47: Weekly risk prompt (Monday 8:00 AM) ─────────────────────
    from app.scheduler.jobs import create_weekly_risk_prompt

    scheduler.add_job(
        create_weekly_risk_prompt,
        trigger=CronTrigger(
            day_of_week="mon",
            hour=8, minute=0,
            timezone=settings.timezone,
        ),
        id="create_weekly_risk_prompt",
        name="Weekly Risk Tolerance Prompt",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    # ── Phase 47: AI weekly review (Sunday 21:00) ─────────────────────────
    from app.scheduler.jobs import generate_weekly_review

    scheduler.add_job(
        generate_weekly_review,
        trigger=CronTrigger(
            day_of_week="sun",
            hour=21, minute=0,
            timezone=settings.timezone,
        ),
        id="generate_weekly_review",
        name="AI Weekly Performance Review",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    logger.info("Goal jobs: create_weekly_risk_prompt (Mon 08:00), generate_weekly_review (Sun 21:00, also chained from weekly_behavior_analysis)")

    # ── Real-time WebSocket jobs (Phase 16) ──────────────────────────────────
    from app.scheduler.jobs import realtime_price_poll, realtime_heartbeat

    scheduler.add_job(
        realtime_price_poll,
        trigger=IntervalTrigger(seconds=settings.realtime_poll_interval),
        id="realtime_price_poll",
        name="Real-Time Price Poll",
        replace_existing=True,
        misfire_grace_time=30,
    )

    scheduler.add_job(
        realtime_heartbeat,
        trigger=IntervalTrigger(seconds=15),
        id="realtime_heartbeat",
        name="Real-Time Heartbeat",
        replace_existing=True,
        misfire_grace_time=15,
    )

    logger.info(
        f"Real-time jobs: realtime_price_poll (every {settings.realtime_poll_interval}s), "
        f"realtime_heartbeat (every 15s)"
    )

    # Register job chaining listener (Phase 2 + Phase 4 + Phase 12)
    scheduler.add_listener(_on_job_executed, events.EVENT_JOB_EXECUTED)
    # Register failure notification listener (Phase 6 — ERR-05)
    scheduler.add_listener(_on_job_error, events.EVENT_JOB_ERROR)
    logger.info(
        "Job chaining registered: "
        "daily_price_crawl_upcom → [indicators → AI → news → sentiment → combined → trading_signal → hnx_upcom_analysis → pick_generation → pick_outcome_check → consecutive_loss_check] + [corporate_action_check]"
    )
    logger.info("Failure notification listener registered for EVENT_JOB_ERROR")
