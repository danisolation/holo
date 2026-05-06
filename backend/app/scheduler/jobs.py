"""Scheduled job functions with resilience.

Each job creates its own database session (jobs run outside of HTTP
request context, so they can't use FastAPI's Depends(get_db)).

Resilience pattern per CONTEXT.md decisions:
- D-06: Retry failed tickers once (re-batch only failures)
- D-07: Retry inside job functions, not wrapping them
- D-08/D-09: Permanently failed items go to dead-letter queue
- D-10: Complete failure raises → EVENT_JOB_ERROR → logged as CRITICAL
- D-13/D-14: One job_executions row per run, not per ticker
- Pitfall 2: Partial failure returns normally (chain continues);
  complete failure raises (chain breaks)
"""
import asyncio
from datetime import date, timedelta

from loguru import logger
from sqlalchemy import select

from app.database import async_session
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.services.price_service import PriceService
from app.services.ticker_service import TickerService
from app.services.financial_service import FinancialService
from app.services.job_execution_service import JobExecutionService
from app.services.dead_letter_service import DeadLetterService
from app.resilience import CircuitOpenError

VALID_EXCHANGES = ("HOSE",)


def _determine_status(result: dict) -> str:
    """Determine job status from crawl/compute results."""
    success = result.get("success", 0)
    failed = result.get("failed", 0)
    if success == 0 and failed > 0:
        return "failed"
    elif failed > 0:
        return "partial"
    return "success"


def _build_summary(result: dict, retried: int = 0, dlq_count: int = 0) -> dict:
    """Build standardized result_summary for job tracking."""
    return {
        "tickers_processed": result.get("success", 0),
        "tickers_failed": result.get("failed", 0),
        "tickers_skipped": result.get("skipped", 0),
        "failed_symbols": result.get("failed_symbols", []),
        "retried_count": retried,
        "dlq_count": dlq_count,
    }


async def _dlq_failures(session, job_type: str, failed_symbols: list[str], retry_count: int = 1):
    """Send permanently failed symbols to dead-letter queue."""
    if not failed_symbols:
        return
    dlq_svc = DeadLetterService(session)
    for symbol in failed_symbols:
        await dlq_svc.add(job_type, symbol, "Persistent failure after retry", retry_count)


async def _get_watchlist_ticker_map(session) -> dict[str, int]:
    """Resolve watchlist symbols to {symbol: ticker_id} for ticker_filter.

    JOINs UserWatchlist.symbol → Ticker.symbol → returns {symbol: Ticker.id}.
    Returns empty dict if watchlist is empty or no symbols match active tickers.
    """
    from app.models.user_watchlist import UserWatchlist
    from app.models.ticker import Ticker

    stmt = (
        select(Ticker.symbol, Ticker.id)
        .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
        .where(Ticker.is_active == True)
    )
    result = await session.execute(stmt)
    return {row[0]: row[1] for row in result.fetchall()}


async def daily_price_crawl():
    """Daily OHLCV crawl with retry + DLQ.

    Runs Mon-Fri at 15:30 Asia/Ho_Chi_Minh.
    Retries failed tickers once (D-06). DLQs permanent failures (D-08).
    Returns normally on partial failure (chain continues).
    Raises on complete failure (chain breaks → Telegram alert).
    """
    logger.info("=== DAILY PRICE CRAWL START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_price_crawl")
        try:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            result = await service.crawl_daily()

            # D-06: Retry failed tickers only (one re-batch attempt)
            failed_symbols = result.get("failed_symbols", [])
            retried = len(failed_symbols)
            if failed_symbols:
                logger.info(f"Retrying {retried} failed tickers...")
                ticker_map = await service.ticker_service.get_ticker_id_map()
                today = date.today().isoformat()
                start = (date.today() - timedelta(days=5)).isoformat()
                retry_map = {s: ticker_map[s] for s in failed_symbols if s in ticker_map}
                retry_result = await service._crawl_batch(
                    list(retry_map.keys()), retry_map, start, today
                )
                result["success"] += retry_result.get("success", 0)
                result["failed"] = retry_result.get("failed", 0)
                result["failed_symbols"] = retry_result.get("failed_symbols", [])

            # D-08: DLQ permanently failed tickers
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_price_crawl", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, retried, len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY PRICE CRAWL COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete crawl failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY PRICE CRAWL FAILED: {e} ===")
            raise


async def daily_price_crawl_for_exchange(exchange: str):
    """Exchange-parameterized daily OHLCV crawl.

    Called by cron trigger: HOSE at 15:30 Mon-Fri.
    Reuses the same resilience pattern as daily_price_crawl but scoped to one exchange.
    """
    if exchange not in VALID_EXCHANGES:
        raise ValueError(f"Invalid exchange: {exchange}. Must be one of {VALID_EXCHANGES}")
    logger.info(f"=== DAILY PRICE CRAWL ({exchange}) START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start(f"daily_price_crawl_{exchange.lower()}")
        try:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            result = await service.crawl_daily(exchange=exchange)

            # D-06: Retry failed tickers only
            failed_symbols = result.get("failed_symbols", [])
            retried = len(failed_symbols)
            if failed_symbols:
                logger.info(f"Retrying {retried} failed {exchange} tickers...")
                ticker_map = await service.ticker_service.get_ticker_id_map(exchange=exchange)
                today = date.today().isoformat()
                start = (date.today() - timedelta(days=5)).isoformat()
                retry_map = {s: ticker_map[s] for s in failed_symbols if s in ticker_map}
                retry_result = await service._crawl_batch(
                    list(retry_map.keys()), retry_map, start, today
                )
                result["success"] += retry_result.get("success", 0)
                result["failed"] = retry_result.get("failed", 0)
                result["failed_symbols"] = retry_result.get("failed_symbols", [])

            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, f"daily_price_crawl_{exchange.lower()}", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, retried, len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY PRICE CRAWL ({exchange}) COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError(f"Complete {exchange} crawl failure: all tickers failed")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY PRICE CRAWL ({exchange}) FAILED: {e} ===")
            raise


async def weekly_ticker_refresh():
    """Weekly ticker list refresh — sync HOSE listing.

    Runs Sunday 10:00. Syncs HOSE tickers only.
    """
    logger.info("=== WEEKLY TICKER REFRESH START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("weekly_ticker_refresh")
        try:
            crawler = VnstockCrawler()
            service = TickerService(session, crawler)
            combined_result = {}
            for exchange in VALID_EXCHANGES:
                logger.info(f"Refreshing {exchange} ticker list...")
                result = await service.fetch_and_sync_tickers(exchange=exchange)
                combined_result[exchange] = result

            summary = {"result": combined_result}
            await job_svc.complete(execution, status="success", result_summary=summary)
            await session.commit()
            logger.info(f"=== WEEKLY TICKER REFRESH COMPLETE: {combined_result} ===")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== WEEKLY TICKER REFRESH FAILED: {e} ===")
            raise


async def weekly_financial_crawl():
    """Weekly financial data crawl with DLQ.

    Runs Saturday 08:00. Fetches latest quarterly financial ratios.
    """
    logger.info("=== WEEKLY FINANCIAL CRAWL START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("weekly_financial_crawl")
        try:
            crawler = VnstockCrawler()
            service = FinancialService(session, crawler)
            result = await service.crawl_financials(period="quarter")

            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "weekly_financial_crawl", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== WEEKLY FINANCIAL CRAWL COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete financial crawl failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== WEEKLY FINANCIAL CRAWL FAILED: {e} ===")
            raise


async def daily_indicator_compute():
    """Compute technical indicators with DLQ.

    Triggered after daily_price_crawl via job chaining.
    """
    logger.info("=== DAILY INDICATOR COMPUTE START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_indicator_compute")
        try:
            from app.services.indicator_service import IndicatorService
            service = IndicatorService(session)
            result = await service.compute_all_tickers()

            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_indicator_compute", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY INDICATOR COMPUTE COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete indicator compute failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY INDICATOR COMPUTE FAILED: {e} ===")
            raise


def _merge_ai_failed_symbols(results: dict) -> list[str]:
    """Extract unique failed symbols across all AI analysis types."""
    all_failed: set[str] = set()
    for analysis_result in results.values():
        if isinstance(analysis_result, dict):
            all_failed.update(analysis_result.get("failed_symbols", []))
    return list(all_failed)


def _sum_ai_results(results: dict) -> dict:
    """Aggregate success/failed counts across AI analysis types."""
    total_success = 0
    total_failed = 0
    for analysis_result in results.values():
        if isinstance(analysis_result, dict):
            total_success += analysis_result.get("success", 0)
            total_failed += analysis_result.get("failed", 0)
    failed_symbols = _merge_ai_failed_symbols(results)
    return {"success": total_success, "failed": total_failed, "failed_symbols": failed_symbols}


async def daily_ai_analysis():
    """Run Gemini AI analysis with DLQ.

    Triggered after daily_indicator_compute via job chaining.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY AI ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_ai_analysis")
        try:
            # Phase 53: Watchlist gating (WL-01)
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily AI analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            logger.info(f"Watchlist gating: analyzing {len(ticker_filter)} tickers")

            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="both", ticker_filter=ticker_filter
            )

            result = _sum_ai_results(results)
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_ai_analysis", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY AI ANALYSIS COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete AI analysis failure: all tickers failed")

        except ValueError as e:
            await job_svc.complete(execution, status="skipped", result_summary={"reason": str(e)})
            await session.commit()
            logger.warning(f"=== DAILY AI ANALYSIS SKIPPED: {e} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY AI ANALYSIS FAILED: {e} ===")
            raise


async def daily_news_crawl():
    """Crawl CafeF news with DLQ.

    Triggered after daily_ai_analysis via job chaining.
    """
    logger.info("=== DAILY NEWS CRAWL START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_news_crawl")
        try:
            # Centralized ticker map — queried once, passed to crawler
            ticker_service = TickerService(session)
            ticker_map = await ticker_service.get_ticker_id_map()
            logger.info(f"Loaded ticker map: {len(ticker_map)} tickers for news crawl")

            from app.crawlers.cafef_crawler import CafeFCrawler
            crawler = CafeFCrawler(session)
            result = await crawler.crawl_all_tickers(ticker_map=ticker_map)

            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_news_crawl", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY NEWS CRAWL COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete news crawl failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY NEWS CRAWL FAILED: {e} ===")
            raise


async def daily_sentiment_analysis():
    """Run Gemini sentiment analysis with DLQ.

    Triggered after daily_news_crawl via job chaining.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY SENTIMENT ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_sentiment_analysis")
        try:
            # Phase 53: Watchlist gating (WL-01)
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily sentiment analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            logger.info(f"Watchlist gating: sentiment for {len(ticker_filter)} tickers")

            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="sentiment", ticker_filter=ticker_filter
            )

            result = _sum_ai_results(results)
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_sentiment_analysis", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY SENTIMENT ANALYSIS COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete sentiment analysis failure")

        except ValueError as e:
            await job_svc.complete(execution, status="skipped", result_summary={"reason": str(e)})
            await session.commit()
            logger.warning(f"=== DAILY SENTIMENT ANALYSIS SKIPPED: {e} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY SENTIMENT ANALYSIS FAILED: {e} ===")
            raise


async def daily_combined_analysis():
    """Run Gemini combined recommendation with DLQ.

    Triggered after daily_sentiment_analysis via job chaining.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY COMBINED ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_combined_analysis")
        try:
            # Phase 53: Watchlist gating (WL-01)
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily combined analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            logger.info(f"Watchlist gating: combined for {len(ticker_filter)} tickers")

            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="combined", ticker_filter=ticker_filter
            )

            result = _sum_ai_results(results)
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_combined_analysis", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY COMBINED ANALYSIS COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete combined analysis failure")

        except ValueError as e:
            await job_svc.complete(execution, status="skipped", result_summary={"reason": str(e)})
            await session.commit()
            logger.warning(f"=== DAILY COMBINED ANALYSIS SKIPPED: {e} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY COMBINED ANALYSIS FAILED: {e} ===")
            raise


async def daily_trading_signal_analysis():
    """Run Gemini trading signal analysis with DLQ.

    Phase 19: Generates dual-direction (LONG + BEARISH) trading plans.
    Triggered after daily_combined_analysis via job chaining.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY TRADING SIGNAL ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_trading_signal_analysis")
        try:
            # Phase 53: Watchlist gating (WL-01)
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily trading signal analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            logger.info(f"Watchlist gating: trading signals for {len(ticker_filter)} tickers")

            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="trading_signal", ticker_filter=ticker_filter
            )

            result = _sum_ai_results(results)
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_trading_signal_analysis", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY TRADING SIGNAL ANALYSIS COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete trading signal analysis failure")

        except ValueError as e:
            await job_svc.complete(execution, status="skipped", result_summary={"reason": str(e)})
            await session.commit()
            logger.warning(f"=== DAILY TRADING SIGNAL ANALYSIS SKIPPED: {e} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY TRADING SIGNAL ANALYSIS FAILED: {e} ===")
            raise




async def daily_pick_generation():
    """Generate daily stock picks after all analysis completes.

    Chains after daily_trading_signal. Scores existing trading signals,
    filters by capital/safety, generates Vietnamese explanations via Gemini.
    """
    logger.info("=== DAILY PICK GENERATION START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_pick_generation")
        try:
            # Phase 53: Watchlist gating (WL-02)
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily pick generation")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "picked": 0, "almost": 0},
                )
                await session.commit()
                return
            watchlist_symbols = set(ticker_filter.keys())
            logger.info(f"Watchlist gating: picking from {len(watchlist_symbols)} tickers")

            from app.services.pick_service import PickService

            service = PickService(session)
            result = await service.generate_daily_picks(watchlist_symbols=watchlist_symbols)
            status = "success" if result.get("picked", 0) > 0 else "partial"
            await job_svc.complete(
                execution,
                status=status,
                result_summary=result,
            )
            await session.commit()
            logger.info(f"=== DAILY PICK GENERATION DONE: {result} ===")
        except Exception as e:
            logger.error(f"Pick generation failed: {e}")
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            raise


# ── Phase 45: Pick outcome tracking ─────────────────────────────────────────


async def daily_pick_outcome_check():
    """Check pending picks and update outcomes from DailyPrice data.

    Chains after daily_pick_generation. Idempotent — only updates picks
    still in 'pending' status. No external API calls, just DB reads/writes.
    """
    logger.info("=== DAILY PICK OUTCOME CHECK START ===")
    async with async_session() as session:
        from app.services.pick_service import PickService

        service = PickService(session)
        result = await service.compute_pick_outcomes()
        logger.info(f"=== DAILY PICK OUTCOME CHECK DONE: {result} ===")


# ── Real-time WebSocket jobs (Phase 16) ─────────────────────────────────────


async def realtime_price_poll():
    """Poll VCI price board and broadcast to WebSocket clients.

    Runs every 30s (configurable). Only polls VCI when market is open
    AND clients are subscribed. Sends market status to all clients.

    Uses module-level singleton so the in-memory price cache persists.
    """
    from app.services.realtime_price_service import (
        is_market_open,
        get_market_session,
        get_realtime_price_service,
    )
    from app.ws.prices import connection_manager

    market_open = is_market_open()
    session = get_market_session()

    # Always send market status so clients know current state
    await connection_manager.send_market_status(is_open=market_open, session=session)

    if not market_open:
        return

    # Only poll if there are subscribed symbols
    if not connection_manager.get_all_subscribed_symbols():
        return

    service = get_realtime_price_service()
    await service.poll_and_broadcast()


async def realtime_heartbeat():
    """Send heartbeat to all connected WebSocket clients.

    Runs every 15s to keep connections alive through proxies/NAT.
    """
    from app.ws.prices import connection_manager

    await connection_manager.send_heartbeat()


# ── Phase 46: Behavior tracking & adaptive strategy ─────────────────────────


async def weekly_behavior_analysis():
    """Weekly batch: detect trading habits + refresh sector preferences.

    Per CONTEXT.md: runs Sunday 20:00 via scheduler.
    Step 1: Detect all trading habits (BEHV-02)
    Step 2: Compute sector preferences (ADPT-02)
    """
    logger.info("=== WEEKLY BEHAVIOR ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("weekly_behavior_analysis")
        try:
            from app.services.behavior_service import BehaviorService

            service = BehaviorService(session)
            # Step 1: Detect all trading habits (BEHV-02)
            habit_result = await service.detect_all_habits()
            # Step 2: Compute sector preferences (ADPT-02)
            sector_result = await service.compute_sector_preferences()
            summary = {
                "habits_detected": habit_result,
                "sectors_updated": len(sector_result),
            }
            await job_svc.complete(execution, status="success", result_summary=summary)
            await session.commit()
            logger.info(f"=== WEEKLY BEHAVIOR ANALYSIS DONE: {summary} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"Weekly behavior analysis failed: {e}")
            raise


async def daily_consecutive_loss_check():
    """Daily: check if last 3 SELL trades are all losses → create risk suggestion.

    Per CONTEXT.md: chains after daily_pick_outcome_check. ADPT-01.
    """
    logger.info("=== DAILY CONSECUTIVE LOSS CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_consecutive_loss_check")
        try:
            from app.services.behavior_service import BehaviorService

            service = BehaviorService(session)
            suggestion = await service.check_consecutive_losses()
            summary = {"suggestion_created": suggestion is not None}
            if suggestion:
                summary["suggestion"] = suggestion
            await job_svc.complete(execution, status="success", result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY CONSECUTIVE LOSS CHECK DONE: {summary} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"Daily consecutive loss check failed: {e}")
            raise


# ── Phase 47: Goals & weekly reviews ────────────────────────────────────────


async def create_weekly_risk_prompt():
    """Create weekly risk tolerance prompt for the user.

    Per GOAL-02: runs Monday 8:00 AM via scheduler.
    Creates a pending prompt (auto-expires previous unanswered ones).
    """
    logger.info("=== CREATE WEEKLY RISK PROMPT START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("create_weekly_risk_prompt")
        try:
            from app.services.goal_service import GoalService

            service = GoalService(session)
            prompt = await service.create_weekly_prompt()
            await job_svc.complete(
                execution,
                status="success",
                result_summary={
                    "week_start": str(prompt.week_start),
                    "risk_level_before": prompt.risk_level_before,
                },
            )
            await session.commit()
            logger.info(f"=== CREATE WEEKLY RISK PROMPT DONE: week_start={prompt.week_start} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"Create weekly risk prompt failed: {e}")
            raise


async def generate_weekly_review():
    """Generate AI weekly performance review via Gemini.

    Per GOAL-03: runs Sunday 21:00 via scheduler, also chained from
    weekly_behavior_analysis (Sun 20:00). Gathers week's data and
    calls Gemini with structured output for Vietnamese coaching review.
    """
    logger.info("=== GENERATE WEEKLY REVIEW START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("generate_weekly_review")
        try:
            from app.services.goal_service import GoalService

            service = GoalService(session)
            result = await service.generate_review()
            await job_svc.complete(
                execution,
                status="success",
                result_summary={"result": result},
            )
            await session.commit()
            logger.info(f"=== GENERATE WEEKLY REVIEW DONE: {result[:80] if result else 'empty'}... ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"Generate weekly review failed: {e}")
            raise


# ── Phase 52: Discovery scoring engine ──────────────────────────────────────


# ── Phase 65: AI Accuracy Tracking ──────────────────────────────────────────


async def daily_accuracy_tracking():
    """Backfill AI prediction accuracy by comparing signals against actual prices.

    Chains after daily_consecutive_loss_check. Checks combined analysis signals
    from 1, 3, and 7 days ago against actual closing prices.
    """
    logger.info("=== DAILY ACCURACY TRACKING START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_accuracy_tracking")
        try:
            from app.services.accuracy_tracking_service import AccuracyTrackingService

            service = AccuracyTrackingService(session)
            result = await service.backfill_accuracy()
            await job_svc.complete(
                execution,
                status="success",
                result_summary=result,
            )
            await session.commit()
            logger.info(f"=== DAILY ACCURACY TRACKING DONE: {result} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"Daily accuracy tracking failed: {e}")
            raise


# ── Phase 58: Morning AI refresh chain ──────────────────────────────────────


async def morning_price_crawl_hose():
    """Morning pre-market price crawl for HOSE (8:30 AM Mon-Fri).

    Reuses daily crawl logic. Chains to morning_indicator_compute
    via _on_job_executed (shortened chain, no discovery/news/sentiment).
    """
    await daily_price_crawl_for_exchange("HOSE")


async def morning_indicator_compute():
    """Morning indicator compute — part of shortened morning chain."""
    logger.info("=== MORNING INDICATOR COMPUTE START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("morning_indicator_compute")
        try:
            from app.services.indicator_service import IndicatorService
            service = IndicatorService(session)
            result = await service.compute_all_tickers()

            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "morning_indicator_compute", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== MORNING INDICATOR COMPUTE COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete morning indicator compute failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== MORNING INDICATOR COMPUTE FAILED: {e} ===")
            raise


async def morning_ai_analysis():
    """Morning AI analysis — part of shortened morning chain.

    Runs technical+fundamental analysis for watchlist tickers only.
    """
    logger.info("=== MORNING AI ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("morning_ai_analysis")
        try:
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping morning AI analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            logger.info(f"Morning watchlist gating: analyzing {len(ticker_filter)} tickers")

            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="both", ticker_filter=ticker_filter
            )

            result = _sum_ai_results(results)
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "morning_ai_analysis", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== MORNING AI ANALYSIS COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete morning AI analysis failure: all tickers failed")

        except ValueError as e:
            await job_svc.complete(execution, status="skipped", result_summary={"reason": str(e)})
            await session.commit()
            logger.warning(f"=== MORNING AI ANALYSIS SKIPPED: {e} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== MORNING AI ANALYSIS FAILED: {e} ===")
            raise


async def morning_trading_signal_analysis():
    """Morning trading signal analysis — part of shortened morning chain.

    Generates trading signals for watchlist tickers only.
    Final step in morning chain (no picks/discovery in morning).
    """
    logger.info("=== MORNING TRADING SIGNAL ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("morning_trading_signal_analysis")
        try:
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping morning trading signal analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            logger.info(f"Morning watchlist gating: trading signals for {len(ticker_filter)} tickers")

            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="trading_signal", ticker_filter=ticker_filter
            )

            result = _sum_ai_results(results)
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "morning_trading_signal_analysis", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== MORNING TRADING SIGNAL ANALYSIS COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete morning trading signal analysis failure")

        except ValueError as e:
            await job_svc.complete(execution, status="skipped", result_summary={"reason": str(e)})
            await session.commit()
            logger.warning(f"=== MORNING TRADING SIGNAL ANALYSIS SKIPPED: {e} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== MORNING TRADING SIGNAL ANALYSIS FAILED: {e} ===")
            raise


async def daily_discovery_scoring():
    """Score all HOSE tickers for discovery.

    Triggered after daily_indicator_compute via job chaining.
    Pure computation — no external API calls. Reads from DB, scores, writes to DB.
    """
    logger.info("=== DAILY DISCOVERY SCORING START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_discovery_scoring")
        try:
            from app.services.discovery_service import DiscoveryService
            service = DiscoveryService(session)
            result = await service.score_all_tickers()

            status = _determine_status(result)
            summary = _build_summary(result)
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY DISCOVERY SCORING COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete discovery scoring failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY DISCOVERY SCORING FAILED: {e} ===")
            raise


async def daily_rumor_crawl():
    """Crawl all rumor sources for watchlist tickers.

    Sources: Fireant (community) + F319 (forum) + VnExpress (news) + Vietstock (news).
    Triggered after daily_trading_signal via job chaining.
    Phase 63/69: Part of rumor intelligence pipeline.
    """
    logger.info("=== DAILY RUMOR CRAWL START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_rumor_crawl")
        try:
            # Centralized ticker map — queried once, shared across all crawlers
            ticker_map = await _get_watchlist_ticker_map(session)
            logger.info(f"Loaded ticker map: {len(ticker_map)} tickers (shared across crawlers)")

            # 1. Fireant community posts (rate-limited, runs alone)
            from app.crawlers.fireant_crawler import FireantCrawler
            crawler = FireantCrawler(session)
            result = await crawler.crawl_watchlist_tickers(ticker_map=ticker_map)

            # 2. RSS crawlers (independent domains, run concurrently)
            # Each gets its own session — AsyncSession is not safe for concurrent use
            from app.crawlers.f319_crawler import F319Crawler
            from app.crawlers.vnexpress_crawler import VnExpressCrawler
            from app.crawlers.vietstock_crawler import VietstockCrawler

            async with async_session() as f319_session, \
                       async_session() as vnex_session, \
                       async_session() as vs_session:
                f319 = F319Crawler(f319_session)
                vnexpress = VnExpressCrawler(vnex_session)
                vietstock = VietstockCrawler(vs_session)

                f319_result, vnexpress_result, vietstock_result = await asyncio.gather(
                    f319.crawl_rss(ticker_map=ticker_map),
                    vnexpress.crawl_rss(ticker_map=ticker_map),
                    vietstock.crawl_rss(ticker_map=ticker_map),
                )

            # Merge results
            result["total_posts"] = (
                result.get("total_posts", 0)
                + f319_result.get("total_posts", 0)
                + vnexpress_result.get("total_posts", 0)
                + vietstock_result.get("total_posts", 0)
            )
            result["success"] = (
                result.get("success", 0)
                + f319_result.get("success", 0)
                + vnexpress_result.get("success", 0)
                + vietstock_result.get("success", 0)
            )

            # result shape: {success, failed, total_posts, failed_symbols}
            final_failed = result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_rumor_crawl", final_failed)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(final_failed))
            summary["total_posts"] = result.get("total_posts", 0)
            summary["f319_posts"] = f319_result.get("total_posts", 0)
            summary["vnexpress_posts"] = vnexpress_result.get("total_posts", 0)
            summary["vietstock_posts"] = vietstock_result.get("total_posts", 0)
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY RUMOR CRAWL COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete rumor crawl failure: all tickers failed")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY RUMOR CRAWL FAILED: {e} ===")
            raise


async def daily_rumor_scoring():
    """Score crawled rumors with Gemini AI credibility/impact assessment.

    Triggered after daily_rumor_crawl via job chaining.
    Phase 63: Part of rumor intelligence pipeline.
    """
    logger.info("=== DAILY RUMOR SCORING START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_rumor_scoring")
        try:
            from app.services.rumor_scoring_service import RumorScoringService
            service = RumorScoringService(session)
            ticker_results = await service.score_all_tickers()

            # Convert {symbol: bool} to standard result dict
            success = sum(1 for v in ticker_results.values() if v)
            failed = sum(1 for v in ticker_results.values() if not v)
            failed_symbols = [s for s, v in ticker_results.items() if not v]
            result = {"success": success, "failed": failed, "failed_symbols": failed_symbols}

            await _dlq_failures(session, "daily_rumor_scoring", failed_symbols)

            status = _determine_status(result)
            summary = _build_summary(result, dlq_count=len(failed_symbols))
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY RUMOR SCORING COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete rumor scoring failure: all tickers failed")

        except ValueError as e:
            # Missing GEMINI_API_KEY — skip gracefully (same pattern as daily_ai_analysis)
            logger.warning(f"Rumor scoring skipped: {e}")
            if execution.status == "running":
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": str(e)},
                )
                await session.commit()
            return

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY RUMOR SCORING FAILED: {e} ===")
            raise

