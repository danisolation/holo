"""Scheduled job functions with resilience.

Each job creates its own database session (jobs run outside of HTTP
request context, so they can't use FastAPI's Depends(get_db)).

Resilience pattern per CONTEXT.md decisions:
- D-06: Retry failed tickers once (re-batch only failures)
- D-07: Retry inside job functions, not wrapping them
- D-08/D-09: Permanently failed items go to dead-letter queue
- D-10: Complete failure raises → EVENT_JOB_ERROR → Telegram alert
- D-13/D-14: One job_executions row per run, not per ticker
- Pitfall 2: Partial failure returns normally (chain continues);
  complete failure raises (chain breaks)
"""
from datetime import date

from loguru import logger

from app.database import async_session
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.services.price_service import PriceService
from app.services.ticker_service import TickerService
from app.services.financial_service import FinancialService
from app.services.job_execution_service import JobExecutionService
from app.services.dead_letter_service import DeadLetterService
from app.resilience import CircuitOpenError

VALID_EXCHANGES = ("HOSE", "HNX", "UPCOM")


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
                start = date.today().replace(day=max(1, date.today().day - 5)).isoformat()
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

    Called by staggered cron triggers: HOSE at 15:30, HNX at 16:00, UPCOM at 16:30.
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
                start = date.today().replace(day=max(1, date.today().day - 5)).isoformat()
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
    """Weekly ticker list refresh — sync listing for all exchanges.

    Runs Sunday 10:00. Syncs HOSE, HNX, and UPCOM sequentially.
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
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(analysis_type="both")

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
            from app.crawlers.cafef_crawler import CafeFCrawler
            crawler = CafeFCrawler(session)
            result = await crawler.crawl_all_tickers()

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
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(analysis_type="sentiment")

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
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(analysis_type="combined")

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
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(analysis_type="trading_signal")

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


async def daily_corporate_action_check():
    """Crawl corporate events from VNDirect.

    Triggered after daily_price_crawl via job chaining.
    """
    logger.info("=== DAILY CORPORATE ACTION CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_corporate_action_check")
        try:
            from app.crawlers.corporate_event_crawler import CorporateEventCrawler

            crawler = CorporateEventCrawler(session)
            crawl_result = await crawler.crawl_all_tickers()

            # DLQ permanently failed tickers
            crawl_failed = crawl_result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_corporate_action_check", crawl_failed)

            new_events = crawl_result.get("new_events", 0)

            status = "success"
            total_failed = crawl_result.get("failed", 0)
            if total_failed > 0 and crawl_result.get("success", 0) == 0:
                status = "failed"
            elif total_failed > 0:
                status = "partial"

            summary = {
                "events_crawled": crawl_result.get("total_events", 0),
                "new_events": new_events,
                "tickers_failed": total_failed,
                "failed_symbols": crawl_failed,
            }
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY CORPORATE ACTION CHECK COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete corporate action check failure")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY CORPORATE ACTION CHECK FAILED: {e} ===")
            raise


async def daily_hnx_upcom_analysis():
    """Tiered AI analysis for watchlisted HNX/UPCOM tickers.

    Chained after daily_combined completes. Analyzes only tickers
    in the UserWatchlist for HNX/UPCOM, capped at 50 per CONTEXT.md.
    """
    logger.info("=== DAILY HNX/UPCOM ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_hnx_upcom_analysis")
        try:
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            result = await service.analyze_watchlisted_tickers(
                exchanges=["HNX", "UPCOM"], max_extra=50
            )
            summary = {"result": result}
            await job_svc.complete(execution, status="success", result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY HNX/UPCOM ANALYSIS COMPLETE: {result} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY HNX/UPCOM ANALYSIS FAILED: {e} ===")
            raise


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

