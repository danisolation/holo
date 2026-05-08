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
    "weekly_ticker_refresh": "Weekly Ticker Refresh",
    "weekly_financial_crawl": "Weekly Financial Crawl",
    "daily_indicator_compute_triggered": "Daily Indicator Compute",
    "daily_indicator_compute_manual": "Daily Indicator Compute",
    "daily_discovery_scoring_triggered": "Daily Discovery Scoring",
    "daily_discovery_scoring_manual": "Daily Discovery Scoring",
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
    "daily_rumor_crawl_triggered": "Daily Rumor Crawl",
    "daily_rumor_crawl_manual": "Daily Rumor Crawl",
    "daily_rumor_scoring_triggered": "Daily Rumor Scoring",
    "daily_rumor_scoring_manual": "Daily Rumor Scoring",
    "daily_unified_analysis_triggered": "Daily Unified Analysis",
    "daily_unified_analysis_manual": "Daily Unified Analysis",
    "daily_pick_generation_triggered": "Daily Pick Generation",
    "daily_pick_generation_manual": "Daily Pick Generation",
    "daily_pick_outcome_check_triggered": "Daily Pick Outcome Check",
    "daily_pick_outcome_check_manual": "Daily Pick Outcome Check",
    "weekly_behavior_analysis": "Weekly Behavior Analysis",
    "daily_consecutive_loss_check": "Daily Consecutive Loss Check",
    "daily_consecutive_loss_check_triggered": "Daily Consecutive Loss Check",
    # Phase 65: Accuracy tracking
    "daily_accuracy_tracking": "Daily AI Accuracy Tracking",
    "daily_accuracy_tracking_triggered": "Daily AI Accuracy Tracking",
    "create_weekly_risk_prompt": "Weekly Risk Tolerance Prompt",
    "generate_weekly_review": "AI Weekly Performance Review",
    "generate_weekly_review_triggered": "AI Weekly Performance Review",
    "realtime_price_poll": "Real-Time Price Poll",
    "realtime_heartbeat": "Real-Time Heartbeat",
    # Phase 93-94: Intraday retention & aggregation
    "daily_intraday_cleanup": "Daily Intraday Cleanup",
    "daily_intraday_aggregate": "Daily Intraday Aggregate",
    "daily_intraday_aggregate_triggered": "Daily Intraday Aggregate",
    # Phase 58: Morning AI refresh chain
    "morning_price_crawl_hose": "Morning Price Crawl (HOSE)",
    "morning_indicator_compute_triggered": "Morning Indicator Compute",
    "morning_ai_analysis_triggered": "Morning AI Analysis",
    "morning_trading_signal_triggered": "Morning Trading Signal",
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

    if event.job_id == "morning_price_crawl_hose":
        # Phase 58: Morning shortened chain (price → indicators → AI → trading signals)
        from app.scheduler.jobs import morning_indicator_compute
        logger.info("Morning chain: morning_price_crawl_hose → morning_indicator_compute")
        scheduler.add_job(
            morning_indicator_compute,
            id="morning_indicator_compute_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id == "morning_indicator_compute_triggered":
        # Morning AI analysis disabled — on-demand only
        logger.info("Morning chain: morning_indicator_compute completed (AI analysis skipped — on-demand)")
    # morning_trading_signal_triggered ends chain (no pick generation in morning)
    elif event.job_id in ("daily_intraday_aggregate", "daily_intraday_aggregate_triggered"):
        # Phase 94: Chain aggregate → indicator compute
        from app.scheduler.jobs import daily_indicator_compute
        logger.info("Chaining: daily_intraday_aggregate → daily_indicator_compute")
        scheduler.add_job(
            daily_indicator_compute,
            id="daily_indicator_compute_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id == "daily_price_crawl_hose":
        from app.scheduler.jobs import daily_indicator_compute
        logger.info("Chaining: daily_price_crawl_hose → daily_indicator_compute")
        scheduler.add_job(
            daily_indicator_compute,
            id="daily_indicator_compute_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_indicator_compute_triggered", "daily_indicator_compute_manual"):
        from app.scheduler.jobs import daily_discovery_scoring
        logger.info("Chaining: daily_indicator_compute → daily_discovery_scoring")
        scheduler.add_job(
            daily_discovery_scoring,
            id="daily_discovery_scoring_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_discovery_scoring_triggered", "daily_discovery_scoring_manual"):
        # AI analysis disabled from scheduler — now on-demand only
        # Skip directly to news crawl
        from app.scheduler.jobs import daily_news_crawl
        logger.info("Chaining: daily_discovery_scoring → daily_news_crawl (AI analysis skipped — on-demand)")
        scheduler.add_job(
            daily_news_crawl,
            id="daily_news_crawl_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_news_crawl_triggered", "daily_news_crawl_manual"):
        # Sentiment/combined/trading_signal AI analysis disabled from scheduler — on-demand only
        # Skip directly to rumor crawl
        from app.scheduler.jobs import daily_rumor_crawl
        logger.info("Chaining: daily_news_crawl → daily_rumor_crawl (AI analysis skipped — on-demand)")
        scheduler.add_job(
            daily_rumor_crawl,
            id="daily_rumor_crawl_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_rumor_crawl_triggered", "daily_rumor_crawl_manual"):
        # Phase 63: Chain rumor crawl → rumor scoring
        from app.scheduler.jobs import daily_rumor_scoring
        logger.info("Chaining: daily_rumor_crawl → daily_rumor_scoring")
        scheduler.add_job(
            daily_rumor_scoring,
            id="daily_rumor_scoring_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_rumor_scoring_triggered", "daily_rumor_scoring_manual"):
        # Phase 88 / v19.0: Chain rumor scoring → unified analysis
        from app.scheduler.jobs import daily_unified_analysis
        logger.info("Chaining: daily_rumor_scoring → daily_unified_analysis")
        scheduler.add_job(
            daily_unified_analysis,
            id="daily_unified_analysis_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_unified_analysis_triggered", "daily_unified_analysis_manual"):
        # Phase 88 / v19.0: Chain unified analysis → pick generation
        from app.scheduler.jobs import daily_pick_generation
        logger.info("Chaining: daily_unified_analysis → daily_pick_generation")
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
    elif event.job_id in ("daily_consecutive_loss_check_triggered",):
        # Phase 65: Chain to accuracy tracking after consecutive loss check
        from app.scheduler.jobs import daily_accuracy_tracking
        logger.info("Chaining: daily_consecutive_loss_check → daily_accuracy_tracking")
        scheduler.add_job(
            daily_accuracy_tracking,
            id="daily_accuracy_tracking_triggered",
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

    # HOSE-only price crawl at 15:30
    EXCHANGE_CRAWL_SCHEDULE = {
        "HOSE": {"hour": 15, "minute": 30},
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

    # ── Real-time VCI polling jobs (Phase 16 + Phase 92) ────────────────────
    # Always poll ALL HOSE symbols for intraday storage, regardless of WS mode
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

    # ── Phase 93: Intraday retention cleanup (01:00 daily) ─────────────
    from app.scheduler.jobs import daily_intraday_cleanup

    scheduler.add_job(
        daily_intraday_cleanup,
        trigger=CronTrigger(
            hour=1, minute=0,
            timezone=settings.timezone,
        ),
        id="daily_intraday_cleanup",
        name="Daily Intraday Cleanup",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    # ── Phase 94: End-of-day aggregation (14:50 Mon-Fri) ───────────────
    from app.scheduler.jobs import daily_intraday_aggregate

    scheduler.add_job(
        daily_intraday_aggregate,
        trigger=CronTrigger(
            hour=14, minute=50,
            day_of_week="mon-fri",
            timezone=settings.timezone,
        ),
        id="daily_intraday_aggregate",
        name="Daily Intraday Aggregate",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info("Intraday jobs: daily_intraday_cleanup (01:00), daily_intraday_aggregate (14:50 Mon-Fri)")

    # ── Phase 58: Morning AI refresh (8:30 AM Mon-Fri) ─────────────────
    from app.scheduler.jobs import morning_price_crawl_hose

    scheduler.add_job(
        morning_price_crawl_hose,
        trigger=CronTrigger(
            hour=8, minute=30,
            day_of_week="mon-fri",
            timezone=settings.timezone,
        ),
        id="morning_price_crawl_hose",
        name="Morning Pre-Market Price Crawl (HOSE)",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info(f"Morning refresh: morning_price_crawl_hose (Mon-Fri 08:30 {settings.timezone})")

    # Register job chaining listener (Phase 2 + Phase 4 + Phase 12)
    scheduler.add_listener(_on_job_executed, events.EVENT_JOB_EXECUTED)
    # Register failure notification listener (Phase 6 — ERR-05)
    scheduler.add_listener(_on_job_error, events.EVENT_JOB_ERROR)
    logger.info(
        "Job chaining registered: "
        "daily_price_crawl_hose → [indicators → discovery_scoring → news → rumor_crawl → rumor_scoring → pick_generation → pick_outcome_check → consecutive_loss_check → accuracy_tracking] (AI analysis: on-demand only), "
        "morning_price_crawl_hose → [indicators] (AI analysis: on-demand only)"
    )
    logger.info("Failure notification listener registered for EVENT_JOB_ERROR")
