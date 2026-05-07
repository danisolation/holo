"""Context gathering for AI analysis — pure DB queries.

Extracted from AIAnalysisService: 5 _get_*_context methods.
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
from app.models.rumor_score import RumorScore


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

        # Phase 67: Volume profile (CTX-01)
        vol_result = await self.session.execute(
            select(DailyPrice.volume)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date.desc())
            .limit(20)
        )
        volumes = [int(r[0]) for r in vol_result.all()]
        if volumes:
            avg_vol_20 = sum(volumes) / len(volumes)
            context["avg_volume_20d"] = round(avg_vol_20)
            latest_vol = volumes[0]
            context["latest_volume"] = latest_vol
            if avg_vol_20 > 0:
                context["relative_volume"] = round(latest_vol / avg_vol_20, 2)
            # Volume trend: compare first half vs second half avg
            if len(volumes) >= 10:
                recent_avg = sum(volumes[:10]) / 10
                older_avg = sum(volumes[10:]) / len(volumes[10:])
                if older_avg > 0:
                    vol_change = (recent_avg - older_avg) / older_avg * 100
                    context["volume_trend"] = "increasing" if vol_change > 10 else (
                        "decreasing" if vol_change < -10 else "stable"
                    )
                    context["volume_change_pct"] = round(vol_change, 1)

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

    # --- Batch methods for O(1) query scaling ---

    async def batch_get_technical_contexts(
        self, ticker_ids: dict[str, int]
    ) -> dict[str, dict]:
        """Batch-fetch technical contexts for all tickers in O(1) queries.

        Args:
            ticker_ids: {symbol: ticker_id} mapping

        Returns:
            {symbol: context_dict} — only tickers with indicator data included.
        """
        if not ticker_ids:
            return {}

        id_list = list(ticker_ids.values())
        id_to_symbol = {v: k for k, v in ticker_ids.items()}

        def _to_float(val: Decimal | None) -> float | None:
            return float(val) if val is not None else None

        # Query 1: Last 5 TechnicalIndicator rows per ticker via window function
        from sqlalchemy import literal_column
        rn_col = sa_func.row_number().over(
            partition_by=TechnicalIndicator.ticker_id,
            order_by=TechnicalIndicator.date.desc(),
        ).label("rn")
        ind_subq = (
            select(TechnicalIndicator, rn_col)
            .where(TechnicalIndicator.ticker_id.in_(id_list))
            .subquery()
        )
        ind_result = await self.session.execute(
            select(ind_subq).where(ind_subq.c.rn <= 5).order_by(
                ind_subq.c.ticker_id, ind_subq.c.date.asc()
            )
        )
        ind_rows = ind_result.all()

        # Group by ticker_id
        from collections import defaultdict
        indicators_by_ticker: dict[int, list] = defaultdict(list)
        for row in ind_rows:
            indicators_by_ticker[row.ticker_id].append(row)

        if not indicators_by_ticker:
            return {}

        # Query 2: Latest close price per ticker
        price_rn = sa_func.row_number().over(
            partition_by=DailyPrice.ticker_id,
            order_by=DailyPrice.date.desc(),
        ).label("rn")
        price_subq = (
            select(DailyPrice.ticker_id, DailyPrice.close, price_rn)
            .where(DailyPrice.ticker_id.in_(id_list))
            .subquery()
        )
        price_result = await self.session.execute(
            select(price_subq.c.ticker_id, price_subq.c.close)
            .where(price_subq.c.rn == 1)
        )
        latest_prices: dict[int, float] = {
            row.ticker_id: float(row.close) for row in price_result.all()
        }

        # Query 3: Last 20 volumes per ticker for volume profile
        vol_rn = sa_func.row_number().over(
            partition_by=DailyPrice.ticker_id,
            order_by=DailyPrice.date.desc(),
        ).label("rn")
        vol_subq = (
            select(DailyPrice.ticker_id, DailyPrice.volume, vol_rn)
            .where(DailyPrice.ticker_id.in_(id_list))
            .subquery()
        )
        vol_result = await self.session.execute(
            select(vol_subq.c.ticker_id, vol_subq.c.volume)
            .where(vol_subq.c.rn <= 20)
            .order_by(vol_subq.c.ticker_id, vol_subq.c.rn.asc())
        )
        volumes_by_ticker: dict[int, list[int]] = defaultdict(list)
        for row in vol_result.all():
            volumes_by_ticker[row.ticker_id].append(int(row.volume))

        # Build per-ticker context dicts
        results: dict[str, dict] = {}
        for tid, rows in indicators_by_ticker.items():
            symbol = id_to_symbol.get(tid)
            if symbol is None:
                continue

            latest = rows[-1]

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

            # Latest close price + SMA distance percentages
            close_val = latest_prices.get(tid)
            if close_val is not None:
                context["latest_close"] = close_val
                for sma_key in ("sma_20", "sma_50", "sma_200"):
                    sma_val = context.get(sma_key)
                    if sma_val is not None and sma_val != 0:
                        pct = (close_val - sma_val) / sma_val * 100
                        context[f"price_vs_{sma_key}_pct"] = round(pct, 2)

            # Volume profile
            volumes = volumes_by_ticker.get(tid, [])
            if volumes:
                avg_vol_20 = sum(volumes) / len(volumes)
                context["avg_volume_20d"] = round(avg_vol_20)
                latest_vol = volumes[0]
                context["latest_volume"] = latest_vol
                if avg_vol_20 > 0:
                    context["relative_volume"] = round(latest_vol / avg_vol_20, 2)
                if len(volumes) >= 10:
                    recent_avg = sum(volumes[:10]) / 10
                    older_avg = sum(volumes[10:]) / len(volumes[10:])
                    if older_avg > 0:
                        vol_change = (recent_avg - older_avg) / older_avg * 100
                        context["volume_trend"] = "increasing" if vol_change > 10 else (
                            "decreasing" if vol_change < -10 else "stable"
                        )
                        context["volume_change_pct"] = round(vol_change, 1)

            results[symbol] = context

        return results

    async def batch_get_fundamental_contexts(
        self, ticker_ids: dict[str, int]
    ) -> dict[str, dict]:
        """Batch-fetch fundamental contexts for all tickers in O(1) queries.

        Args:
            ticker_ids: {symbol: ticker_id} mapping

        Returns:
            {symbol: context_dict} — only tickers with financial data included.
        """
        if not ticker_ids:
            return {}

        id_list = list(ticker_ids.values())
        id_to_symbol = {v: k for k, v in ticker_ids.items()}

        def _to_float(val: Decimal | None) -> float | None:
            return float(val) if val is not None else None

        # Single query: latest Financial per ticker via window function
        rn_col = sa_func.row_number().over(
            partition_by=Financial.ticker_id,
            order_by=[Financial.year.desc(), Financial.quarter.desc().nullslast()],
        ).label("rn")
        fin_subq = (
            select(Financial, rn_col)
            .where(Financial.ticker_id.in_(id_list))
            .subquery()
        )
        fin_result = await self.session.execute(
            select(fin_subq).where(fin_subq.c.rn == 1)
        )
        fin_rows = fin_result.all()

        results: dict[str, dict] = {}
        for row in fin_rows:
            symbol = id_to_symbol.get(row.ticker_id)
            if symbol is None:
                continue
            results[symbol] = {
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

        return results

    async def batch_get_sentiment_contexts(
        self, ticker_ids: dict[str, int]
    ) -> dict[str, dict]:
        """Batch-fetch sentiment contexts for all tickers in O(1) queries.

        Args:
            ticker_ids: {symbol: ticker_id} mapping

        Returns:
            {symbol: context_dict} — every ticker gets an entry (empty list if no news).
        """
        if not ticker_ids:
            return {}

        id_list = list(ticker_ids.values())
        id_to_symbol = {v: k for k, v in ticker_ids.items()}
        cutoff = datetime.now() - timedelta(days=settings.cafef_news_days)

        # Single query: all news titles for all tickers
        result = await self.session.execute(
            select(NewsArticle.ticker_id, NewsArticle.title)
            .where(
                NewsArticle.ticker_id.in_(id_list),
                NewsArticle.published_at >= cutoff,
            )
            .order_by(NewsArticle.ticker_id, NewsArticle.published_at.desc())
        )
        news_rows = result.all()

        # Group by ticker_id in Python
        from collections import defaultdict
        titles_by_ticker: dict[int, list[str]] = defaultdict(list)
        for row in news_rows:
            title = _sanitize_title(row.title)
            if title:
                titles_by_ticker[row.ticker_id].append(title)

        # Build results — every ticker gets an entry
        results: dict[str, dict] = {}
        for symbol, tid in ticker_ids.items():
            titles = titles_by_ticker.get(tid, [])
            results[symbol] = {
                "news_titles": titles,
                "news_count": len(titles),
            }

        return results

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
            context["tech_reasoning"] = tech.reasoning or ""
        else:
            context["tech_signal"] = "N/A"
            context["tech_score"] = "N/A"
            context["tech_reasoning"] = ""

        if fund:
            context["fund_signal"] = fund.signal
            context["fund_score"] = fund.score
            context["fund_reasoning"] = fund.reasoning or ""
        else:
            context["fund_signal"] = "N/A"
            context["fund_score"] = "N/A"
            context["fund_reasoning"] = ""

        if sent:
            context["sent_signal"] = sent.signal
            context["sent_score"] = sent.score
            context["sent_reasoning"] = sent.reasoning or ""
        else:
            # Graceful degradation: sentiment defaults to neutral (per CONTEXT.md)
            context["sent_signal"] = "neutral"
            context["sent_score"] = 5
            context["sent_reasoning"] = "Không có tin tức đặc biệt."

        # Include current price to prevent AI hallucination of key_levels
        price_result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        latest_price = price_result.scalar_one_or_none()
        if latest_price is not None:
            context["current_price"] = float(latest_price)

        # Phase 64: Include rumor intelligence in combined analysis (AIUP-01)
        rumor = await self.get_rumor_context(ticker_id, symbol)
        if rumor:
            context["rumor_direction"] = rumor["direction"]
            context["rumor_credibility"] = rumor["credibility_score"]
            context["rumor_impact"] = rumor["impact_score"]
            context["rumor_reasoning"] = rumor["reasoning"]
            context["rumor_key_claims"] = rumor["key_claims"]

        # Phase 67: Sector peer comparison (CTX-02)
        from app.models.ticker import Ticker
        ticker_row = await self.session.execute(
            select(Ticker.sector).where(Ticker.id == ticker_id)
        )
        sector = ticker_row.scalar_one_or_none()
        if sector:
            # Get avg combined scores for tickers in the same sector
            sector_avg_result = await self.session.execute(
                select(sa_func.avg(AIAnalysis.score))
                .join(Ticker, Ticker.id == AIAnalysis.ticker_id)
                .where(
                    AIAnalysis.analysis_type == AnalysisType.COMBINED,
                    Ticker.sector == sector,
                    AIAnalysis.analysis_date >= date.today() - timedelta(days=7),
                )
            )
            sector_avg = sector_avg_result.scalar_one_or_none()
            if sector_avg is not None:
                context["sector"] = sector
                context["sector_avg_score"] = round(float(sector_avg), 1)

        return context

    async def get_rumor_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get latest rumor score for a ticker.

        Returns dict with credibility, impact, direction, key_claims, reasoning.
        Returns None if no rumor score exists (ticker gracefully skipped in prompts).
        """
        result = await self.session.execute(
            select(RumorScore)
            .where(RumorScore.ticker_id == ticker_id)
            .order_by(RumorScore.scored_date.desc())
            .limit(1)
        )
        score = result.scalar_one_or_none()

        if score is None:
            return None

        return {
            "credibility_score": score.credibility_score,
            "impact_score": score.impact_score,
            "direction": score.direction,
            "key_claims": score.key_claims or [],
            "reasoning": score.reasoning or "",
        }

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
            # Phase 67: 52-week price percentile (CTX-03)
            high_52 = float(row[0])
            low_52 = float(row[1])
            if high_52 > low_52:
                percentile = (context["current_price"] - low_52) / (high_52 - low_52) * 100
                context["price_percentile_52w"] = round(percentile, 1)

        # Phase 67: Volume-price correlation (CTX-03)
        vp_result = await self.session.execute(
            select(DailyPrice.close, DailyPrice.volume)
            .where(
                DailyPrice.ticker_id == ticker_id,
                DailyPrice.date >= date.today() - timedelta(days=20),
            )
            .order_by(DailyPrice.date.asc())
        )
        vp_rows = vp_result.all()
        if len(vp_rows) >= 5:
            prices_list = [float(r[0]) for r in vp_rows]
            vols_list = [int(r[1]) for r in vp_rows]
            # Simple correlation: are prices and volumes moving together?
            price_up_days = sum(1 for i in range(1, len(prices_list)) if prices_list[i] > prices_list[i-1])
            vol_up_on_price_up = sum(
                1 for i in range(1, len(prices_list))
                if prices_list[i] > prices_list[i-1] and vols_list[i] > vols_list[i-1]
            )
            if price_up_days > 0:
                vp_corr = vol_up_on_price_up / price_up_days
                context["volume_price_alignment"] = (
                    "strong" if vp_corr >= 0.7 else "moderate" if vp_corr >= 0.4 else "weak"
                )

        # Phase 64: Include rumor context for trading signals (AIUP-02)
        rumor = await self.get_rumor_context(ticker_id, symbol)
        if rumor:
            context["rumor_direction"] = rumor["direction"]
            context["rumor_impact"] = rumor["impact_score"]
            context["rumor_key_claims"] = rumor["key_claims"]

        return context

    # ------------------------------------------------------------------
    # Phase 88 / v19.0: Unified Analysis Context
    # ------------------------------------------------------------------

    async def get_unified_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get comprehensive context for unified analysis — ALL dimensions in one.

        Combines: technical indicators (5-day window + S/R + BBands),
        fundamental metrics, recent news titles, rumor scores,
        current price, 52-week range, volume profile.

        Returns None if no indicator data (minimum requirement).
        """
        # --- Technical indicators ---
        result = await self.session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker_id)
            .order_by(TechnicalIndicator.date.desc())
            .limit(5)
        )
        rows = result.scalars().all()
        if not rows:
            return None

        rows = list(reversed(rows))  # chronological order
        latest = rows[-1]

        def _f(val) -> float | None:
            return float(val) if val is not None else None

        context: dict = {
            # 5-day arrays
            "rsi_14": [_f(r.rsi_14) for r in rows],
            "macd_line": [_f(r.macd_line) for r in rows],
            "macd_signal": [_f(r.macd_signal) for r in rows],
            "macd_histogram": [_f(r.macd_histogram) for r in rows],
            # Latest indicator values
            "sma_20": _f(latest.sma_20),
            "sma_50": _f(latest.sma_50),
            "sma_200": _f(latest.sma_200),
            "ema_12": _f(latest.ema_12),
            "ema_26": _f(latest.ema_26),
            "bb_upper": _f(latest.bb_upper),
            "bb_middle": _f(latest.bb_middle),
            "bb_lower": _f(latest.bb_lower),
            "atr_14": _f(latest.atr_14),
            "adx_14": _f(latest.adx_14),
            "stoch_k_14": _f(latest.stoch_k_14),
            "stoch_d_14": _f(latest.stoch_d_14),
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
            return None

        # RSI zone
        latest_rsi = _f(latest.rsi_14)
        if latest_rsi is not None:
            if latest_rsi < 30:
                context["rsi_zone"] = "oversold"
            elif latest_rsi > 70:
                context["rsi_zone"] = "overbought"
            else:
                context["rsi_zone"] = "neutral"
        else:
            context["rsi_zone"] = "unknown"

        # MACD crossover
        histograms = context["macd_histogram"]
        if len(histograms) >= 2 and histograms[-1] is not None and histograms[-2] is not None:
            if histograms[-1] > 0 and histograms[-2] <= 0:
                context["macd_crossover"] = "bullish"
            elif histograms[-1] < 0 and histograms[-2] >= 0:
                context["macd_crossover"] = "bearish"
            else:
                context["macd_crossover"] = "none"
        else:
            context["macd_crossover"] = "none"

        # --- Current price ---
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

        # SMA distance %
        close_val = context["current_price"]
        for sma_key in ("sma_20", "sma_50", "sma_200"):
            sma_val = context.get(sma_key)
            if sma_val is not None and sma_val != 0:
                pct = (close_val - sma_val) / sma_val * 100
                context[f"price_vs_{sma_key}_pct"] = round(pct, 2)

        # --- 52-week high/low ---
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
        row52 = week52_result.one_or_none()
        if row52 and row52[0] is not None:
            context["week_52_high"] = float(row52[0])
            context["week_52_low"] = float(row52[1])
            high_52 = float(row52[0])
            low_52 = float(row52[1])
            if high_52 > low_52:
                percentile = (context["current_price"] - low_52) / (high_52 - low_52) * 100
                context["price_percentile_52w"] = round(percentile, 1)

        # --- Volume profile ---
        vol_result = await self.session.execute(
            select(DailyPrice.close, DailyPrice.volume)
            .where(
                DailyPrice.ticker_id == ticker_id,
                DailyPrice.date >= date.today() - timedelta(days=20),
            )
            .order_by(DailyPrice.date.desc())
        )
        vol_rows = vol_result.all()
        if vol_rows:
            volumes = [int(r[1]) for r in vol_rows]
            avg_vol = sum(volumes) / len(volumes)
            context["avg_volume_20d"] = round(avg_vol)
            context["latest_volume"] = volumes[0]
            if avg_vol > 0:
                context["relative_volume"] = round(volumes[0] / avg_vol, 2)
            if len(volumes) >= 10:
                recent_avg = sum(volumes[:10]) / 10
                older_avg = sum(volumes[10:]) / len(volumes[10:])
                if older_avg > 0:
                    vol_change = (recent_avg - older_avg) / older_avg * 100
                    context["volume_trend"] = "increasing" if vol_change > 10 else (
                        "decreasing" if vol_change < -10 else "stable"
                    )
                    context["volume_change_pct"] = round(vol_change, 1)

        # --- Fundamental metrics ---
        fin_result = await self.session.execute(
            select(Financial)
            .where(Financial.ticker_id == ticker_id)
            .order_by(Financial.year.desc(), Financial.quarter.desc().nullslast())
            .limit(1)
        )
        fin_row = fin_result.scalar_one_or_none()
        if fin_row:
            context["fundamental"] = {
                "period": fin_row.period,
                "pe": float(fin_row.pe) if fin_row.pe else None,
                "pb": float(fin_row.pb) if fin_row.pb else None,
                "eps": float(fin_row.eps) if fin_row.eps else None,
                "roe": float(fin_row.roe) if fin_row.roe else None,
                "roa": float(fin_row.roa) if fin_row.roa else None,
                "revenue_growth": float(fin_row.revenue_growth) if fin_row.revenue_growth else None,
                "profit_growth": float(fin_row.profit_growth) if fin_row.profit_growth else None,
                "current_ratio": float(fin_row.current_ratio) if fin_row.current_ratio else None,
                "debt_to_equity": float(fin_row.debt_to_equity) if fin_row.debt_to_equity else None,
            }

        # --- News titles ---
        cutoff = datetime.now() - timedelta(days=settings.cafef_news_days)
        news_result = await self.session.execute(
            select(NewsArticle.title)
            .where(
                NewsArticle.ticker_id == ticker_id,
                NewsArticle.published_at >= cutoff,
            )
            .order_by(NewsArticle.published_at.desc())
        )
        titles = [_sanitize_title(row[0]) for row in news_result.all()]
        context["news_titles"] = [t for t in titles if t]

        # --- Rumor intelligence ---
        rumor = await self.get_rumor_context(ticker_id, symbol)
        if rumor:
            context["rumor_direction"] = rumor["direction"]
            context["rumor_credibility"] = rumor["credibility_score"]
            context["rumor_impact"] = rumor["impact_score"]
            context["rumor_key_claims"] = rumor["key_claims"]
            context["rumor_reasoning"] = rumor["reasoning"]

        return context

