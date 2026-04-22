"""Context gathering for AI analysis — pure DB queries.

Extracted from AIAnalysisService: 5 _get_*_context methods.
BacktestContextBuilder overrides 3 methods with date-aware queries.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.daily_price import DailyPrice
from app.models.financial import Financial
from app.models.news_article import NewsArticle
from app.models.technical_indicator import TechnicalIndicator


def _sanitize_title(title: str, max_length: int = 300) -> str:
    """Strip control characters and enforce length on a news title."""
    title = "".join(c for c in title if not unicodedata.category(c).startswith("C"))
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) > max_length:
        title = title[:max_length] + "…"
    return title


class ContextBuilder:
    """Gathers DB context for each analysis type."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_technical_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get 5-day indicator window for a ticker.

        Returns dict with indicator arrays, RSI zone, and MACD crossover state.
        Returns None if no indicator data exists.
        """
        result = await self.session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker_id)
            .order_by(TechnicalIndicator.date.desc())
            .limit(5)
        )
        rows = result.scalars().all()

        if not rows:
            return None

        # Reverse to chronological order (oldest first)
        rows = list(reversed(rows))

        def _to_float(val: Decimal | None) -> float | None:
            return float(val) if val is not None else None

        latest = rows[-1]

        # Build 5-day indicator arrays
        context: dict = {
            "rsi_14": [_to_float(r.rsi_14) for r in rows],
            "macd_line": [_to_float(r.macd_line) for r in rows],
            "macd_signal": [_to_float(r.macd_signal) for r in rows],
            "macd_histogram": [_to_float(r.macd_histogram) for r in rows],
            "sma_20": _to_float(latest.sma_20),
            "sma_50": _to_float(latest.sma_50),
            "sma_200": _to_float(latest.sma_200),
            "ema_12": _to_float(latest.ema_12),
            "ema_26": _to_float(latest.ema_26),
            "bb_upper": _to_float(latest.bb_upper),
            "bb_middle": _to_float(latest.bb_middle),
            "bb_lower": _to_float(latest.bb_lower),
        }

        # RSI zone classification
        latest_rsi = _to_float(latest.rsi_14)
        if latest_rsi is not None:
            if latest_rsi < 30:
                context["rsi_zone"] = "oversold"
            elif latest_rsi > 70:
                context["rsi_zone"] = "overbought"
            else:
                context["rsi_zone"] = "neutral"
        else:
            context["rsi_zone"] = "unknown"

        # MACD crossover detection
        histograms = [_to_float(r.macd_histogram) for r in rows]
        if len(histograms) >= 2 and histograms[-1] is not None and histograms[-2] is not None:
            if histograms[-1] > 0 and histograms[-2] <= 0:
                context["macd_crossover"] = "bullish"
            elif histograms[-1] < 0 and histograms[-2] >= 0:
                context["macd_crossover"] = "bearish"
            else:
                context["macd_crossover"] = "none"
        else:
            context["macd_crossover"] = "none"

        # Latest close price + SMA distance percentages (AI-10)
        price_result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        latest_close_decimal = price_result.scalar_one_or_none()

        if latest_close_decimal is not None:
            close_val = float(latest_close_decimal)
            context["latest_close"] = close_val
            for sma_key in ("sma_20", "sma_50", "sma_200"):
                sma_val = context.get(sma_key)
                if sma_val is not None and sma_val != 0:
                    pct = (close_val - sma_val) / sma_val * 100
                    context[f"price_vs_{sma_key}_pct"] = round(pct, 2)

        return context

    async def get_fundamental_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get latest financial ratios for a ticker.

        Returns dict with P/E, P/B, ROE, ROA, growth rates, debt ratios.
        Returns None if no financial data exists.
        """
        result = await self.session.execute(
            select(Financial)
            .where(Financial.ticker_id == ticker_id)
            .order_by(Financial.year.desc(), Financial.quarter.desc().nullslast())
            .limit(1)
        )
        row = result.scalar_one_or_none()

        if row is None:
            return None

        def _to_float(val: Decimal | None) -> float | None:
            return float(val) if val is not None else None

        return {
            "period": row.period,
            "pe": _to_float(row.pe),
            "pb": _to_float(row.pb),
            "eps": _to_float(row.eps),
            "roe": _to_float(row.roe),
            "roa": _to_float(row.roa),
            "revenue_growth": _to_float(row.revenue_growth),
            "profit_growth": _to_float(row.profit_growth),
            "current_ratio": _to_float(row.current_ratio),
            "debt_to_equity": _to_float(row.debt_to_equity),
        }

    async def get_sentiment_context(
        self, ticker_id: int, symbol: str
    ) -> dict:
        """Get recent news titles for a ticker.

        Returns dict with news_titles list and news_count.
        Always returns a dict (never None) — tickers with 0 news get empty list.
        Per CONTEXT.md: Gemini handles empty news by scoring neutral.
        """
        cutoff = datetime.now() - timedelta(days=settings.cafef_news_days)

        result = await self.session.execute(
            select(NewsArticle.title)
            .where(
                NewsArticle.ticker_id == ticker_id,
                NewsArticle.published_at >= cutoff,
            )
            .order_by(NewsArticle.published_at.desc())
        )
        titles = [_sanitize_title(row[0]) for row in result.all()]
        titles = [t for t in titles if t]  # drop empty after sanitization

        return {
            "news_titles": titles,
            "news_count": len(titles),
        }

    async def get_combined_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get latest technical, fundamental, and sentiment analyses for a ticker.

        Returns dict with tech_signal, tech_score, fund_signal, fund_score,
        sent_signal, sent_score. Returns None if ticker has neither technical
        nor fundamental analysis (nothing to combine).

        Per CONTEXT.md: if sentiment is missing, set sent_signal=neutral, sent_score=5.
        """
        # Fetch latest analysis per type (up to 3 rows)
        result = await self.session.execute(
            select(AIAnalysis)
            .where(AIAnalysis.ticker_id == ticker_id)
            .where(AIAnalysis.analysis_type.in_([
                AnalysisType.TECHNICAL,
                AnalysisType.FUNDAMENTAL,
                AnalysisType.SENTIMENT,
            ]))
            .order_by(AIAnalysis.analysis_date.desc())
        )
        rows = result.scalars().all()

        # Group by type — take the most recent of each
        by_type: dict[str, AIAnalysis] = {}
        for row in rows:
            type_val = row.analysis_type.value if isinstance(row.analysis_type, AnalysisType) else row.analysis_type
            if type_val not in by_type:
                by_type[type_val] = row

        tech = by_type.get("technical")
        fund = by_type.get("fundamental")
        sent = by_type.get("sentiment")

        # Skip tickers with NO tech AND NO fund (per RESEARCH.md pitfall 6)
        if tech is None and fund is None:
            return None

        context = {}

        if tech:
            context["tech_signal"] = tech.signal
            context["tech_score"] = tech.score
        else:
            context["tech_signal"] = "N/A"
            context["tech_score"] = "N/A"

        if fund:
            context["fund_signal"] = fund.signal
            context["fund_score"] = fund.score
        else:
            context["fund_signal"] = "N/A"
            context["fund_score"] = "N/A"

        if sent:
            context["sent_signal"] = sent.signal
            context["sent_score"] = sent.score
        else:
            # Graceful degradation: sentiment defaults to neutral (per CONTEXT.md)
            context["sent_signal"] = "neutral"
            context["sent_score"] = 5

        return context

    async def get_trading_signal_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get comprehensive context for trading signal generation.

        Combines: latest indicators (ATR, ADX, RSI, Stochastic, BBands),
        S/R levels (pivot, support, resistance, fibonacci),
        current price, and 52-week high/low.
        Returns None if no indicator data (skip ticker).
        """
        result = await self.session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker_id)
            .order_by(TechnicalIndicator.date.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest is None:
            return None

        def _f(val) -> float | None:
            return float(val) if val is not None else None

        context = {
            "atr_14": _f(latest.atr_14),
            "adx_14": _f(latest.adx_14),
            "rsi_14": _f(latest.rsi_14),
            "stoch_k_14": _f(latest.stoch_k_14),
            "stoch_d_14": _f(latest.stoch_d_14),
            "bb_upper": _f(latest.bb_upper),
            "bb_middle": _f(latest.bb_middle),
            "bb_lower": _f(latest.bb_lower),
            # Phase 18 S/R levels
            "pivot_point": _f(latest.pivot_point),
            "support_1": _f(latest.support_1),
            "support_2": _f(latest.support_2),
            "resistance_1": _f(latest.resistance_1),
            "resistance_2": _f(latest.resistance_2),
            "fib_236": _f(latest.fib_236),
            "fib_382": _f(latest.fib_382),
            "fib_500": _f(latest.fib_500),
            "fib_618": _f(latest.fib_618),
        }

        # Skip if no ATR data (needed for post-validation)
        if context["atr_14"] is None:
            logger.debug(f"Skipping {symbol} for trading signal: no ATR data")
            return None

        # Latest close price
        price_result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        latest_close = price_result.scalar_one_or_none()
        if latest_close is None:
            return None
        context["current_price"] = float(latest_close)

        # 52-week high/low
        week52_result = await self.session.execute(
            select(
                sa_func.max(DailyPrice.high),
                sa_func.min(DailyPrice.low),
            )
            .where(
                DailyPrice.ticker_id == ticker_id,
                DailyPrice.date >= date.today() - timedelta(days=365),
            )
        )
        row = week52_result.one_or_none()
        if row and row[0] is not None:
            context["week_52_high"] = float(row[0])
            context["week_52_low"] = float(row[1])

        return context


class BacktestContextBuilder(ContextBuilder):
    """Date-aware context builder for backtesting.

    Overrides context-gathering to use as_of_date instead of latest data.
    CRITICAL invariants (no lookahead bias):
    - All queries use WHERE date <= self.as_of_date
    - 52-week high/low computed relative to as_of_date (not date.today())
    - Combined context reads from backtest_analyses (not ai_analyses)
    """

    def __init__(self, session: AsyncSession, run_id: int, as_of_date: date):
        super().__init__(session)
        self.run_id = run_id
        self.as_of_date = as_of_date

    async def get_technical_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get 5-day indicator window up to as_of_date for a ticker.

        Identical to parent logic but adds WHERE date <= self.as_of_date
        to prevent lookahead bias.
        """
        result = await self.session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker_id)
            .where(TechnicalIndicator.date <= self.as_of_date)
            .order_by(TechnicalIndicator.date.desc())
            .limit(5)
        )
        rows = result.scalars().all()

        if not rows:
            return None

        # Reverse to chronological order (oldest first)
        rows = list(reversed(rows))

        def _to_float(val: Decimal | None) -> float | None:
            return float(val) if val is not None else None

        latest = rows[-1]

        # Build 5-day indicator arrays
        context: dict = {
            "rsi_14": [_to_float(r.rsi_14) for r in rows],
            "macd_line": [_to_float(r.macd_line) for r in rows],
            "macd_signal": [_to_float(r.macd_signal) for r in rows],
            "macd_histogram": [_to_float(r.macd_histogram) for r in rows],
            "sma_20": _to_float(latest.sma_20),
            "sma_50": _to_float(latest.sma_50),
            "sma_200": _to_float(latest.sma_200),
            "ema_12": _to_float(latest.ema_12),
            "ema_26": _to_float(latest.ema_26),
            "bb_upper": _to_float(latest.bb_upper),
            "bb_middle": _to_float(latest.bb_middle),
            "bb_lower": _to_float(latest.bb_lower),
        }

        # RSI zone classification
        latest_rsi = _to_float(latest.rsi_14)
        if latest_rsi is not None:
            if latest_rsi < 30:
                context["rsi_zone"] = "oversold"
            elif latest_rsi > 70:
                context["rsi_zone"] = "overbought"
            else:
                context["rsi_zone"] = "neutral"
        else:
            context["rsi_zone"] = "unknown"

        # MACD crossover detection
        histograms = [_to_float(r.macd_histogram) for r in rows]
        if len(histograms) >= 2 and histograms[-1] is not None and histograms[-2] is not None:
            if histograms[-1] > 0 and histograms[-2] <= 0:
                context["macd_crossover"] = "bullish"
            elif histograms[-1] < 0 and histograms[-2] >= 0:
                context["macd_crossover"] = "bearish"
            else:
                context["macd_crossover"] = "none"
        else:
            context["macd_crossover"] = "none"

        # Latest close price + SMA distance percentages — date-filtered
        price_result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .where(DailyPrice.date <= self.as_of_date)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        latest_close_decimal = price_result.scalar_one_or_none()

        if latest_close_decimal is not None:
            close_val = float(latest_close_decimal)
            context["latest_close"] = close_val
            for sma_key in ("sma_20", "sma_50", "sma_200"):
                sma_val = context.get(sma_key)
                if sma_val is not None and sma_val != 0:
                    pct = (close_val - sma_val) / sma_val * 100
                    context[f"price_vs_{sma_key}_pct"] = round(pct, 2)

        return context

    async def get_combined_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get latest technical, fundamental, and sentiment analyses from backtest_analyses.

        CRITICAL: Queries BacktestAnalysis model (not AIAnalysis) filtered by run_id.
        Uses string comparison for analysis_type (column is String(20), not Enum).
        """
        from app.models.backtest import BacktestAnalysis

        result = await self.session.execute(
            select(BacktestAnalysis)
            .where(BacktestAnalysis.run_id == self.run_id)
            .where(BacktestAnalysis.ticker_id == ticker_id)
            .where(BacktestAnalysis.analysis_type.in_([
                "technical",
                "fundamental",
                "sentiment",
            ]))
            .where(BacktestAnalysis.analysis_date <= self.as_of_date)
            .order_by(BacktestAnalysis.analysis_date.desc())
        )
        rows = result.scalars().all()

        # Group by type — take the most recent of each
        by_type: dict[str, BacktestAnalysis] = {}
        for row in rows:
            type_val = row.analysis_type
            if type_val not in by_type:
                by_type[type_val] = row

        tech = by_type.get("technical")
        fund = by_type.get("fundamental")
        sent = by_type.get("sentiment")

        # Skip tickers with NO tech AND NO fund
        if tech is None and fund is None:
            return None

        context = {}

        if tech:
            context["tech_signal"] = tech.signal
            context["tech_score"] = tech.score
        else:
            context["tech_signal"] = "N/A"
            context["tech_score"] = "N/A"

        if fund:
            context["fund_signal"] = fund.signal
            context["fund_score"] = fund.score
        else:
            context["fund_signal"] = "N/A"
            context["fund_score"] = "N/A"

        if sent:
            context["sent_signal"] = sent.signal
            context["sent_score"] = sent.score
        else:
            # Graceful degradation: sentiment defaults to neutral (per CONTEXT.md)
            context["sent_signal"] = "neutral"
            context["sent_score"] = 5

        return context

    async def get_trading_signal_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get comprehensive context for trading signal generation — date-aware.

        Adds WHERE date <= self.as_of_date to all queries.
        52-week high/low computed relative to as_of_date (NOT date.today()).
        """
        result = await self.session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker_id)
            .where(TechnicalIndicator.date <= self.as_of_date)
            .order_by(TechnicalIndicator.date.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest is None:
            return None

        def _f(val) -> float | None:
            return float(val) if val is not None else None

        context = {
            "atr_14": _f(latest.atr_14),
            "adx_14": _f(latest.adx_14),
            "rsi_14": _f(latest.rsi_14),
            "stoch_k_14": _f(latest.stoch_k_14),
            "stoch_d_14": _f(latest.stoch_d_14),
            "bb_upper": _f(latest.bb_upper),
            "bb_middle": _f(latest.bb_middle),
            "bb_lower": _f(latest.bb_lower),
            # S/R levels
            "pivot_point": _f(latest.pivot_point),
            "support_1": _f(latest.support_1),
            "support_2": _f(latest.support_2),
            "resistance_1": _f(latest.resistance_1),
            "resistance_2": _f(latest.resistance_2),
            "fib_236": _f(latest.fib_236),
            "fib_382": _f(latest.fib_382),
            "fib_500": _f(latest.fib_500),
            "fib_618": _f(latest.fib_618),
        }

        # Skip if no ATR data (needed for post-validation)
        if context["atr_14"] is None:
            logger.debug(f"Skipping {symbol} for trading signal: no ATR data")
            return None

        # Latest close price — date-filtered
        price_result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .where(DailyPrice.date <= self.as_of_date)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        latest_close = price_result.scalar_one_or_none()
        if latest_close is None:
            return None
        context["current_price"] = float(latest_close)

        # 52-week high/low — relative to as_of_date (NOT date.today())
        week52_result = await self.session.execute(
            select(
                sa_func.max(DailyPrice.high),
                sa_func.min(DailyPrice.low),
            )
            .where(
                DailyPrice.ticker_id == ticker_id,
                DailyPrice.date >= self.as_of_date - timedelta(days=365),
                DailyPrice.date <= self.as_of_date,
            )
        )
        row = week52_result.one_or_none()
        if row and row[0] is not None:
            context["week_52_high"] = float(row[0])
            context["week_52_low"] = float(row[1])

        return context
