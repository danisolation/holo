"""Analysis endpoints: trigger computation, retrieve results.

Manual triggers run in background (same pattern as system.py crawl triggers).
Result endpoints return latest analysis for a ticker.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import async_session
from app.models.ticker import Ticker
from app.models.news_article import NewsArticle
from app.models.technical_indicator import TechnicalIndicator
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.schemas.analysis import (
    AnalysisTriggerResponse,
    AnalysisResultResponse,
    IndicatorResponse,
    SummaryResponse,
    NewsArticleResponse,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


# --- On-Demand Single-Ticker Analysis ---

@router.post("/{symbol}/analyze-now", response_model=AnalysisTriggerResponse)
async def trigger_on_demand_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
):
    """Trigger on-demand AI analysis for a single ticker.

    Used by the 'Phân tích ngay' button on ticker detail pages.
    Primarily for HNX/UPCOM tickers not in the daily analysis schedule.
    Runs all 4 analysis types in background.
    """
    # Verify ticker exists first (fail fast)
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol.upper())
        ticker_id = ticker.id
        ticker_symbol = ticker.symbol

        # Server-side cooldown: reject if analysis exists within last 5 minutes
        recent = await session.execute(
            select(AIAnalysis)
            .where(
                AIAnalysis.ticker_id == ticker_id,
                AIAnalysis.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            .limit(1)
        )
        if recent.scalar_one_or_none():
            raise HTTPException(
                status_code=429,
                detail="Analysis recently completed. Try again in a few minutes.",
            )

    async def _run():
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            try:
                service = AIAnalysisService(session)
                result = await service.analyze_single_ticker(ticker_id, ticker_symbol)
                logger.info(f"On-demand analysis for {ticker_symbol} complete: {result}")
            except Exception as e:
                logger.error(f"On-demand analysis for {ticker_symbol} failed: {e}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message=f"AI analysis for {ticker_symbol} triggered in background",
        triggered=True,
    )


# --- Trigger Endpoints ---

@router.post("/trigger/indicators", response_model=AnalysisTriggerResponse)
async def trigger_indicator_computation(background_tasks: BackgroundTasks):
    """Manually trigger indicator computation for all tickers (runs in background)."""
    async def _run():
        async with async_session() as session:
            from app.services.indicator_service import IndicatorService
            service = IndicatorService(session)
            result = await service.compute_all_tickers()
            logger.info(f"Manual indicator computation complete: {result}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message="Indicator computation triggered in background",
        triggered=True,
    )


@router.post("/trigger/ai", response_model=AnalysisTriggerResponse)
async def trigger_ai_analysis(
    analysis_type: str = "both",
    background_tasks: BackgroundTasks = None,
):
    """Manually trigger AI analysis for all tickers (runs in background).

    Args:
        analysis_type: 'technical', 'fundamental', or 'both' (default)
    """
    if analysis_type not in ("technical", "fundamental", "both"):
        raise HTTPException(status_code=400, detail="analysis_type must be 'technical', 'fundamental', or 'both'")

    async def _run():
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            try:
                service = AIAnalysisService(session)
                result = await service.analyze_all_tickers(analysis_type=analysis_type)
                logger.info(f"Manual AI analysis complete: {result}")
            except ValueError as e:
                logger.error(f"AI analysis failed: {e}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message=f"AI analysis ({analysis_type}) triggered in background",
        triggered=True,
    )


@router.post("/trigger/news", response_model=AnalysisTriggerResponse)
async def trigger_news_crawl(background_tasks: BackgroundTasks):
    """Manually trigger CafeF news crawl for all tickers (runs in background)."""
    async def _run():
        async with async_session() as session:
            from app.crawlers.cafef_crawler import CafeFCrawler
            crawler = CafeFCrawler(session)
            result = await crawler.crawl_all_tickers()
            logger.info(f"Manual news crawl complete: {result}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message="CafeF news crawl triggered in background",
        triggered=True,
    )


@router.post("/trigger/sentiment", response_model=AnalysisTriggerResponse)
async def trigger_sentiment_analysis(background_tasks: BackgroundTasks):
    """Manually trigger sentiment analysis for all tickers (runs in background)."""
    async def _run():
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            try:
                service = AIAnalysisService(session)
                result = await service.analyze_all_tickers(analysis_type="sentiment")
                logger.info(f"Manual sentiment analysis complete: {result}")
            except ValueError as e:
                logger.error(f"Sentiment analysis failed: {e}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message="Sentiment analysis triggered in background",
        triggered=True,
    )


@router.post("/trigger/combined", response_model=AnalysisTriggerResponse)
async def trigger_combined_analysis(background_tasks: BackgroundTasks):
    """Manually trigger combined recommendation for all tickers (runs in background)."""
    async def _run():
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            try:
                service = AIAnalysisService(session)
                result = await service.analyze_all_tickers(analysis_type="combined")
                logger.info(f"Manual combined analysis complete: {result}")
            except ValueError as e:
                logger.error(f"Combined analysis failed: {e}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message="Combined analysis triggered in background",
        triggered=True,
    )


@router.post("/trigger/trading-signal", response_model=AnalysisTriggerResponse)
async def trigger_trading_signal_analysis(background_tasks: BackgroundTasks):
    """Manually trigger trading signal analysis for all tickers (runs in background).

    Phase 19: Generates dual-direction LONG + BEARISH trading plans via Gemini.
    """
    async def _run():
        async with async_session() as session:
            from app.services.ai_analysis_service import AIAnalysisService
            try:
                service = AIAnalysisService(session)
                result = await service.analyze_all_tickers(analysis_type="trading_signal")
                logger.info(f"Manual trading signal analysis complete: {result}")
            except ValueError as e:
                logger.error(f"Trading signal analysis failed: {e}")

    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message="Trading signal analysis triggered in background",
        triggered=True,
    )


# --- Result Endpoints ---

@router.get("/{symbol}/indicators", response_model=list[IndicatorResponse])
async def get_ticker_indicators(symbol: str, limit: int = 5):
    """Get latest technical indicator values for a ticker.

    Args:
        symbol: Ticker symbol (e.g., 'VNM', 'FPT')
        limit: Number of recent dates to return (default 5, max 500)
    """
    limit = min(limit, 500)
    async with async_session() as session:
        # Resolve symbol to ticker_id
        ticker = await _get_ticker_by_symbol(session, symbol)

        result = await session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker.id)
            .order_by(TechnicalIndicator.date.desc())
            .limit(limit)
        )
        rows = result.scalars().all()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No indicators found for {symbol}")

        # Reverse to ascending date order (query uses DESC to get latest N,
        # but lightweight-charts requires data sorted ASC by time)
        rows = list(reversed(rows))

        return [
            IndicatorResponse(
                ticker_symbol=symbol.upper(),
                date=row.date.isoformat(),
                rsi_14=float(row.rsi_14) if row.rsi_14 is not None else None,
                macd_line=float(row.macd_line) if row.macd_line is not None else None,
                macd_signal=float(row.macd_signal) if row.macd_signal is not None else None,
                macd_histogram=float(row.macd_histogram) if row.macd_histogram is not None else None,
                sma_20=float(row.sma_20) if row.sma_20 is not None else None,
                sma_50=float(row.sma_50) if row.sma_50 is not None else None,
                sma_200=float(row.sma_200) if row.sma_200 is not None else None,
                ema_12=float(row.ema_12) if row.ema_12 is not None else None,
                ema_26=float(row.ema_26) if row.ema_26 is not None else None,
                bb_upper=float(row.bb_upper) if row.bb_upper is not None else None,
                bb_middle=float(row.bb_middle) if row.bb_middle is not None else None,
                bb_lower=float(row.bb_lower) if row.bb_lower is not None else None,
                # Phase 17: new indicators
                atr_14=float(row.atr_14) if row.atr_14 is not None else None,
                adx_14=float(row.adx_14) if row.adx_14 is not None else None,
                plus_di_14=float(row.plus_di_14) if row.plus_di_14 is not None else None,
                minus_di_14=float(row.minus_di_14) if row.minus_di_14 is not None else None,
                stoch_k_14=float(row.stoch_k_14) if row.stoch_k_14 is not None else None,
                stoch_d_14=float(row.stoch_d_14) if row.stoch_d_14 is not None else None,
                # Phase 18: Support & Resistance
                pivot_point=float(row.pivot_point) if row.pivot_point is not None else None,
                support_1=float(row.support_1) if row.support_1 is not None else None,
                support_2=float(row.support_2) if row.support_2 is not None else None,
                resistance_1=float(row.resistance_1) if row.resistance_1 is not None else None,
                resistance_2=float(row.resistance_2) if row.resistance_2 is not None else None,
                fib_236=float(row.fib_236) if row.fib_236 is not None else None,
                fib_382=float(row.fib_382) if row.fib_382 is not None else None,
                fib_500=float(row.fib_500) if row.fib_500 is not None else None,
                fib_618=float(row.fib_618) if row.fib_618 is not None else None,
            )
            for row in rows
        ]


@router.get("/{symbol}/technical", response_model=AnalysisResultResponse)
async def get_technical_analysis(symbol: str):
    """Get latest AI technical analysis for a ticker."""
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        analysis = await _get_latest_analysis(session, ticker.id, AnalysisType.TECHNICAL)
        return AnalysisResultResponse(
            ticker_symbol=symbol.upper(),
            analysis_type="technical",
            analysis_date=analysis.analysis_date.isoformat(),
            signal=analysis.signal,
            score=analysis.score,
            reasoning=analysis.reasoning,
            model_version=analysis.model_version,
        )


@router.get("/{symbol}/fundamental", response_model=AnalysisResultResponse)
async def get_fundamental_analysis(symbol: str):
    """Get latest AI fundamental analysis for a ticker."""
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        analysis = await _get_latest_analysis(session, ticker.id, AnalysisType.FUNDAMENTAL)
        return AnalysisResultResponse(
            ticker_symbol=symbol.upper(),
            analysis_type="fundamental",
            analysis_date=analysis.analysis_date.isoformat(),
            signal=analysis.signal,
            score=analysis.score,
            reasoning=analysis.reasoning,
            model_version=analysis.model_version,
        )


@router.get("/{symbol}/sentiment", response_model=AnalysisResultResponse)
async def get_sentiment_analysis(symbol: str):
    """Get latest AI sentiment analysis for a ticker."""
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        analysis = await _get_latest_analysis(session, ticker.id, AnalysisType.SENTIMENT)
        return AnalysisResultResponse(
            ticker_symbol=symbol.upper(),
            analysis_type="sentiment",
            analysis_date=analysis.analysis_date.isoformat(),
            signal=analysis.signal,
            score=analysis.score,
            reasoning=analysis.reasoning,
            model_version=analysis.model_version,
        )


@router.get("/{symbol}/combined", response_model=AnalysisResultResponse)
async def get_combined_analysis(symbol: str):
    """Get latest AI combined recommendation for a ticker."""
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        analysis = await _get_latest_analysis(session, ticker.id, AnalysisType.COMBINED)
        return AnalysisResultResponse(
            ticker_symbol=symbol.upper(),
            analysis_type="combined",
            analysis_date=analysis.analysis_date.isoformat(),
            signal=analysis.signal,
            score=analysis.score,
            reasoning=analysis.reasoning,
            model_version=analysis.model_version,
        )


@router.get("/{symbol}/trading-signal", response_model=AnalysisResultResponse)
async def get_trading_signal(symbol: str):
    """Get latest AI trading signal analysis for a ticker.

    Phase 19: Returns dual-direction (LONG/BEARISH) trading plan.
    The raw_response JSONB contains full TickerTradingSignal data.
    signal field = recommended direction ('long' or 'bearish', or 'invalid')
    score field = confidence of recommended direction (0-10, 0 = validation failed)
    """
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        analysis = await _get_latest_analysis(session, ticker.id, AnalysisType.TRADING_SIGNAL)
        return AnalysisResultResponse(
            ticker_symbol=symbol.upper(),
            analysis_type="trading_signal",
            analysis_date=analysis.analysis_date.isoformat(),
            signal=analysis.signal,
            score=analysis.score,
            reasoning=analysis.reasoning,
            model_version=analysis.model_version,
            raw_response=analysis.raw_response,  # Phase 20: expose full TickerTradingSignal JSONB
        )


@router.get("/{symbol}/summary", response_model=SummaryResponse)
async def get_analysis_summary(symbol: str):
    """Get full analysis summary for a ticker (all 4 dimensions).

    Returns available analyses — does not 404 if some dimensions are missing.
    Per CONTEXT.md: GET /api/analysis/{symbol}/summary.
    """
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)

        summary_data: dict = {"ticker_symbol": symbol.upper()}

        for analysis_type in [AnalysisType.TECHNICAL, AnalysisType.FUNDAMENTAL,
                              AnalysisType.SENTIMENT, AnalysisType.COMBINED,
                              AnalysisType.TRADING_SIGNAL]:  # Phase 19
            result = await session.execute(
                select(AIAnalysis)
                .where(
                    AIAnalysis.ticker_id == ticker.id,
                    AIAnalysis.analysis_type == analysis_type,
                )
                .order_by(AIAnalysis.analysis_date.desc())
                .limit(1)
            )
            analysis = result.scalar_one_or_none()
            if analysis:
                summary_data[analysis_type.value] = AnalysisResultResponse(
                    ticker_symbol=symbol.upper(),
                    analysis_type=analysis_type.value,
                    analysis_date=analysis.analysis_date.isoformat(),
                    signal=analysis.signal,
                    score=analysis.score,
                    reasoning=analysis.reasoning,
                    model_version=analysis.model_version,
                )

        return SummaryResponse(**summary_data)


@router.get("/{symbol}/news", response_model=list[NewsArticleResponse])
async def get_ticker_news(symbol: str, limit: int = 10):
    """Get latest news articles for a ticker from CafeF.

    Args:
        symbol: Ticker symbol (e.g., 'VNM', 'FPT')
        limit: Number of articles to return (default 10, max 50)
    """
    limit = min(limit, 50)
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.ticker_id == ticker.id)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            NewsArticleResponse(
                title=row.title,
                url=row.url,
                published_at=row.published_at.isoformat(),
            )
            for row in rows
        ]


# --- Helpers ---

async def _get_ticker_by_symbol(session: AsyncSession, symbol: str) -> Ticker:
    """Resolve ticker symbol to Ticker object. Raises 404 if not found."""
    result = await session.execute(
        select(Ticker).where(Ticker.symbol == symbol.upper())
    )
    ticker = result.scalar_one_or_none()
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker '{symbol}' not found")
    return ticker


async def _get_latest_analysis(
    session: AsyncSession, ticker_id: int, analysis_type: AnalysisType
) -> AIAnalysis:
    """Get most recent analysis of given type. Raises 404 if none exists."""
    result = await session.execute(
        select(AIAnalysis)
        .where(
            AIAnalysis.ticker_id == ticker_id,
            AIAnalysis.analysis_type == analysis_type,
        )
        .order_by(AIAnalysis.analysis_date.desc())
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No {analysis_type.value} analysis found for this ticker",
        )
    return analysis
