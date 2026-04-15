"""Scheduled job functions.

Each job creates its own database session (jobs run outside of HTTP
request context, so they can't use FastAPI's Depends(get_db)).
"""
from loguru import logger

from app.database import async_session
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.services.price_service import PriceService
from app.services.ticker_service import TickerService
from app.services.financial_service import FinancialService


async def daily_price_crawl():
    """Daily OHLCV crawl for all active tickers.

    Runs Mon-Fri at 15:30 Asia/Ho_Chi_Minh.
    Creates its own DB session since this runs from the scheduler, not HTTP.
    """
    logger.info("=== DAILY PRICE CRAWL START ===")
    try:
        async with async_session() as session:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            result = await service.crawl_daily()
            logger.info(f"=== DAILY PRICE CRAWL COMPLETE: {result} ===")
    except Exception as e:
        logger.error(f"=== DAILY PRICE CRAWL FAILED: {e} ===")
        raise


async def weekly_ticker_refresh():
    """Weekly ticker list refresh — sync HOSE listing to database.

    Runs Sunday 10:00. Catches IPOs, delistings, suspensions.
    """
    logger.info("=== WEEKLY TICKER REFRESH START ===")
    try:
        async with async_session() as session:
            crawler = VnstockCrawler()
            service = TickerService(session, crawler)
            result = await service.fetch_and_sync_tickers()
            logger.info(f"=== WEEKLY TICKER REFRESH COMPLETE: {result} ===")
    except Exception as e:
        logger.error(f"=== WEEKLY TICKER REFRESH FAILED: {e} ===")
        raise


async def weekly_financial_crawl():
    """Weekly financial data crawl for all active tickers.

    Runs Saturday 08:00. Fetches latest quarterly financial ratios.
    """
    logger.info("=== WEEKLY FINANCIAL CRAWL START ===")
    try:
        async with async_session() as session:
            crawler = VnstockCrawler()
            service = FinancialService(session, crawler)
            result = await service.crawl_financials(period="quarter")
            logger.info(f"=== WEEKLY FINANCIAL CRAWL COMPLETE: {result} ===")
    except Exception as e:
        logger.error(f"=== WEEKLY FINANCIAL CRAWL FAILED: {e} ===")
        raise


async def daily_indicator_compute():
    """Compute technical indicators for all active tickers.

    Triggered automatically after daily_price_crawl via job chaining.
    Can also be triggered manually via API endpoint.
    """
    logger.info("=== DAILY INDICATOR COMPUTE START ===")
    try:
        async with async_session() as session:
            from app.services.indicator_service import IndicatorService
            service = IndicatorService(session)
            result = await service.compute_all_tickers()
            logger.info(f"=== DAILY INDICATOR COMPUTE COMPLETE: {result} ===")
    except Exception as e:
        logger.error(f"=== DAILY INDICATOR COMPUTE FAILED: {e} ===")
        raise


async def daily_ai_analysis():
    """Run Gemini AI analysis for all active tickers.

    Triggered automatically after daily_indicator_compute via job chaining.
    Can also be triggered manually via API endpoint.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY AI ANALYSIS START ===")
    try:
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            result = await service.analyze_all_tickers(analysis_type="both")
            logger.info(f"=== DAILY AI ANALYSIS COMPLETE: {result} ===")
    except ValueError as e:
        logger.warning(f"=== DAILY AI ANALYSIS SKIPPED: {e} ===")
        # ValueError from AIAnalysisService if GEMINI_API_KEY not set
    except Exception as e:
        logger.error(f"=== DAILY AI ANALYSIS FAILED: {e} ===")
        raise


async def daily_news_crawl():
    """Crawl CafeF news for all active tickers.

    Triggered automatically after daily_ai_analysis via job chaining.
    Can also be triggered manually via API endpoint.
    """
    logger.info("=== DAILY NEWS CRAWL START ===")
    try:
        async with async_session() as session:
            from app.crawlers.cafef_crawler import CafeFCrawler
            crawler = CafeFCrawler(session)
            result = await crawler.crawl_all_tickers()
            logger.info(f"=== DAILY NEWS CRAWL COMPLETE: {result} ===")
    except Exception as e:
        logger.error(f"=== DAILY NEWS CRAWL FAILED: {e} ===")
        raise


async def daily_sentiment_analysis():
    """Run Gemini sentiment analysis for all active tickers.

    Triggered automatically after daily_news_crawl via job chaining.
    Can also be triggered manually via API endpoint.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY SENTIMENT ANALYSIS START ===")
    try:
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            result = await service.analyze_all_tickers(analysis_type="sentiment")
            logger.info(f"=== DAILY SENTIMENT ANALYSIS COMPLETE: {result} ===")
    except ValueError as e:
        logger.warning(f"=== DAILY SENTIMENT ANALYSIS SKIPPED: {e} ===")
    except Exception as e:
        logger.error(f"=== DAILY SENTIMENT ANALYSIS FAILED: {e} ===")
        raise


async def daily_combined_analysis():
    """Run Gemini combined recommendation for all active tickers.

    Triggered automatically after daily_sentiment_analysis via job chaining.
    Can also be triggered manually via API endpoint.
    Requires GEMINI_API_KEY to be set.
    """
    logger.info("=== DAILY COMBINED ANALYSIS START ===")
    try:
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            result = await service.analyze_all_tickers(analysis_type="combined")
            logger.info(f"=== DAILY COMBINED ANALYSIS COMPLETE: {result} ===")
    except ValueError as e:
        logger.warning(f"=== DAILY COMBINED ANALYSIS SKIPPED: {e} ===")
    except Exception as e:
        logger.error(f"=== DAILY COMBINED ANALYSIS FAILED: {e} ===")
        raise
