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


async def daily_signal_alert_check():
    """Check watched tickers for signal changes and send Telegram alerts.

    Triggered after daily_combined_analysis via job chaining.
    Never raises — alert failure must not break the pipeline (D-3.4).
    """
    logger.info("=== DAILY SIGNAL ALERT CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_signal_alert_check")
        try:
            from app.telegram.services import AlertService
            service = AlertService(session)
            result = await service.check_signal_changes()
            await job_svc.complete(
                execution, status="success",
                result_summary={"alerts_sent": result},
            )
            await session.commit()
            logger.info(f"=== DAILY SIGNAL ALERT CHECK COMPLETE: {result} alerts sent ===")
        except Exception as e:
            await job_svc.complete(
                execution, status="partial",
                result_summary={"error": str(e)[:200]},
            )
            await session.commit()
            logger.error(f"=== DAILY SIGNAL ALERT CHECK FAILED: {e} ===")


async def daily_price_alert_check():
    """Check price alerts against latest close prices after daily crawl.

    Triggered after daily_price_crawl via job chaining.
    Never raises — alert failure must not break the pipeline (D-3.4).
    """
    logger.info("=== DAILY PRICE ALERT CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_price_alert_check")
        try:
            from app.telegram.services import AlertService
            service = AlertService(session)
            result = await service.check_price_alerts()
            await job_svc.complete(
                execution, status="success",
                result_summary={"alerts_triggered": result},
            )
            await session.commit()
            logger.info(f"=== DAILY PRICE ALERT CHECK COMPLETE: {result} alerts triggered ===")
        except Exception as e:
            await job_svc.complete(
                execution, status="partial",
                result_summary={"error": str(e)[:200]},
            )
            await session.commit()
            logger.error(f"=== DAILY PRICE ALERT CHECK FAILED: {e} ===")


async def daily_summary_send():
    """Send daily market summary via Telegram.

    Runs on cron schedule at 16:00 UTC+7 (after full pipeline completes).
    Never raises — summary failure is non-critical.
    """
    logger.info("=== DAILY SUMMARY SEND START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_summary_send")
        try:
            from app.telegram.services import AlertService
            service = AlertService(session)
            result = await service.send_daily_summary()
            await job_svc.complete(
                execution, status="success",
                result_summary={"sent": result},
            )
            await session.commit()
            logger.info(f"=== DAILY SUMMARY SEND COMPLETE: sent={result} ===")
        except Exception as e:
            await job_svc.complete(
                execution, status="partial",
                result_summary={"error": str(e)[:200]},
            )
            await session.commit()
            logger.error(f"=== DAILY SUMMARY SEND FAILED: {e} ===")


async def daily_corporate_action_check():
    """Crawl corporate events and recompute adjusted prices.

    Triggered after daily_price_crawl via job chaining.
    If new events found, recomputes adjusted_close for all tickers
    and triggers indicator recompute (per D-07-05).
    """
    logger.info("=== DAILY CORPORATE ACTION CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_corporate_action_check")
        try:
            # Phase 1: Crawl events from VNDirect
            from app.crawlers.corporate_event_crawler import CorporateEventCrawler

            crawler = CorporateEventCrawler(session)
            crawl_result = await crawler.crawl_all_tickers()

            # DLQ permanently failed tickers
            crawl_failed = crawl_result.get("failed_symbols", [])
            await _dlq_failures(session, "daily_corporate_action_check", crawl_failed)

            new_events = crawl_result.get("new_events", 0)

            # Phase 2: If new events found, recompute adjusted_close
            adjust_result = {"adjusted": 0, "skipped": 0, "failed": 0, "failed_symbols": []}
            if new_events > 0:
                logger.info(f"Found {new_events} new corporate events — recomputing adjusted prices")
                from app.services.corporate_action_service import CorporateActionService

                service = CorporateActionService(session)
                adjust_result = await service.adjust_all_tickers()

            status = "success"
            total_failed = crawl_result.get("failed", 0) + adjust_result.get("failed", 0)
            if total_failed > 0 and crawl_result.get("success", 0) == 0:
                status = "failed"
            elif total_failed > 0:
                status = "partial"

            summary = {
                "events_crawled": crawl_result.get("total_events", 0),
                "new_events": new_events,
                "tickers_adjusted": adjust_result.get("adjusted", 0),
                "tickers_failed": total_failed,
                "failed_symbols": crawl_failed + adjust_result.get("failed_symbols", []),
            }
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== DAILY CORPORATE ACTION CHECK COMPLETE: {summary} ===")

            if status == "failed":
                raise RuntimeError("Complete corporate action check failure")

            # Phase 3: If adjustments were made, trigger indicator recompute
            if adjust_result.get("adjusted", 0) > 0:
                from app.scheduler.manager import scheduler

                logger.info("Chaining: corporate_action_check → indicator recompute (post-adjustment)")
                scheduler.add_job(
                    daily_indicator_compute,
                    id="daily_indicator_compute_post_corp_action",
                    replace_existing=True,
                    misfire_grace_time=3600,
                )

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY CORPORATE ACTION CHECK FAILED: {e} ===")
            raise


async def daily_exdate_alert_check():
    """Check for upcoming ex-dates and send Telegram alerts.

    Triggered after daily_corporate_action_check via job chaining.
    Never raises — alert failure must not break the pipeline.
    """
    logger.info("=== DAILY EXDATE ALERT CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_exdate_alert_check")
        try:
            from app.services.exdate_alert_service import ExDateAlertService
            service = ExDateAlertService(session)
            result = await service.check_upcoming_exdates()
            await job_svc.complete(
                execution, status="success",
                result_summary={"alerts_sent": result},
            )
            await session.commit()
            logger.info(f"=== DAILY EXDATE ALERT CHECK COMPLETE: {result} alerts sent ===")
        except Exception as e:
            await job_svc.complete(
                execution, status="partial",
                result_summary={"error": str(e)[:200]},
            )
            await session.commit()
            logger.error(f"=== DAILY EXDATE ALERT CHECK FAILED: {e} ===")


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


async def health_alert_check():
    """Proactive health alert check — runs every 30 minutes.

    Per D-15-05: Checks consecutive failures, stale data, pool exhaustion.
    Never-raises pattern (try/except with logging) to avoid polluting
    the scheduler error listener.
    """
    logger.info("=== HEALTH ALERT CHECK START ===")
    try:
        from app.services.health_alert_service import HealthAlertService

        async with async_session() as session:
            svc = HealthAlertService(session)
            await svc.check_and_alert()
        logger.info("=== HEALTH ALERT CHECK COMPLETE ===")
    except Exception as e:
        logger.error(f"=== HEALTH ALERT CHECK FAILED: {e} ===")
