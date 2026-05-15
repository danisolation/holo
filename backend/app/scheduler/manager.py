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
    # Phase 65: Accuracy tracking
    "daily_accuracy_tracking": "Daily AI Accuracy Tracking",
    "daily_accuracy_tracking_triggered": "Daily AI Accuracy Tracking",
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
    "morning_unified_analysis_triggered": "Morning Unified AI Analysis",
    # Phase 98: Simulator auto-sell
    "daily_simulator_sl_tp_check": "Daily Simulator Auto-Sell Check",
    "daily_simulator_sl_tp_check_triggered": "Daily Simulator Auto-Sell Check",
    # Phase 103: Sector intelligence
    "daily_sector_intelligence": "Daily Sector Intelligence",
    "daily_sector_intelligence_triggered": "Daily Sector Intelligence",
    "daily_sector_intelligence_manual": "Daily Sector Intelligence",
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
        from app.scheduler.jobs import morning_unified_analysis
        logger.info("Morning chain: morning_indicator_compute → morning_unified_analysis")
        scheduler.add_job(
            morning_unified_analysis,
            id="morning_unified_analysis_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
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
        # Phase 65: Chain to accuracy tracking after pick outcome check
        from app.scheduler.jobs import daily_accuracy_tracking
        logger.info("Chaining: daily_pick_outcome_check → daily_accuracy_tracking")
        scheduler.add_job(
            daily_accuracy_tracking,
            id="daily_accuracy_tracking_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_accuracy_tracking_triggered", "daily_accuracy_tracking"):
        # Phase 107: Chain to simulator auto-buy after accuracy tracking
        from app.scheduler.jobs import daily_simulator_auto_buy
        logger.info("Chaining: daily_accuracy_tracking → daily_simulator_auto_buy")
        scheduler.add_job(
            daily_simulator_auto_buy,
            id="daily_simulator_auto_buy_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_simulator_auto_buy_triggered", "daily_simulator_auto_buy"):
        # Phase 98→107: Chain to simulator auto-sell check after auto-buy
        from app.scheduler.jobs import daily_simulator_sl_tp_check
        logger.info("Chaining: daily_simulator_auto_buy → daily_simulator_sl_tp_check")
        scheduler.add_job(
            daily_simulator_sl_tp_check,
            id="daily_simulator_sl_tp_check_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id in ("daily_simulator_sl_tp_check_triggered", "daily_simulator_sl_tp_check"):
        # Phase 103: Chain to sector intelligence after simulator check
        from app.scheduler.jobs import daily_sector_intelligence
        logger.info("Chaining: daily_simulator_sl_tp_check → daily_sector_intelligence")
        scheduler.add_job(
            daily_sector_intelligence,
            id="daily_sector_intelligence_triggered",
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
        "daily_price_crawl_hose → [indicators → discovery_scoring → news → rumor_crawl → rumor_scoring → pick_generation → pick_outcome_check → accuracy_tracking → simulator_sl_tp → sector_intelligence] (AI analysis: on-demand only), "
        "morning_price_crawl_hose → [indicators → unified_analysis]"
    )
    logger.info("Failure notification listener registered for EVENT_JOB_ERROR")

    # ── Keep-alive self-ping (prevent Render free tier sleep) ──────────
    async def _self_ping():
        """Ping own health endpoint to prevent Render free tier from sleeping."""
        import httpx
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                resp = await client.get("https://holo-api-1wj4.onrender.com/api/health/summary")
                logger.debug(f"Self-ping: {resp.status_code}")
        except Exception as e:
            logger.debug(f"Self-ping failed (non-fatal): {e}")

    scheduler.add_job(
        _self_ping,
        trigger=IntervalTrigger(minutes=10),
        id="keep_alive_ping",
        name="Keep-Alive Self-Ping",
        replace_existing=True,
        misfire_grace_time=120,
    )
    logger.info("Keep-alive: self-ping every 10 minutes")
