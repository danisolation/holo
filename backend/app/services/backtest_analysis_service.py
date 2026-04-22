"""Date-aware Gemini analysis service for backtesting.

Subclasses AIAnalysisService to make all context queries use `as_of_date`
instead of latest data, and stores results in `backtest_analyses` instead
of `ai_analyses`.

CRITICAL invariants (no lookahead bias):
- All queries use WHERE date <= self.as_of_date
- 52-week high/low computed relative to as_of_date (not date.today())
- Combined context reads from backtest_analyses (not ai_analyses)
- Storage writes to backtest_analyses with run_id
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestAnalysis
from app.models.daily_price import DailyPrice
from app.models.technical_indicator import TechnicalIndicator
from app.services.ai_analysis_service import AIAnalysisService


class BacktestAnalysisService(AIAnalysisService):
    """Date-aware analysis service for backtesting.

    Overrides context-gathering to use as_of_date instead of latest data,
    and storage to write to backtest_analyses instead of ai_analyses.
    """

    def __init__(
        self,
        session: AsyncSession,
        run_id: int,
        as_of_date: date,
        api_key: str | None = None,
    ):
        super().__init__(session, api_key)
        self.run_id = run_id
        self.as_of_date = as_of_date

    # ------------------------------------------------------------------
    # Override 1: _get_technical_context — date-aware indicator query
    # ------------------------------------------------------------------

    async def _get_technical_context(
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

    # ------------------------------------------------------------------
    # Override 2: _get_combined_context — reads backtest_analyses (NOT ai_analyses)
    # ------------------------------------------------------------------

    async def _get_combined_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get latest technical, fundamental, and sentiment analyses from backtest_analyses.

        CRITICAL: Queries BacktestAnalysis model (not AIAnalysis) filtered by run_id.
        Uses string comparison for analysis_type (column is String(20), not Enum).
        """
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

    # ------------------------------------------------------------------
    # Override 3: _get_trading_signal_context — date-aware with 52-week relative
    # ------------------------------------------------------------------

    async def _get_trading_signal_context(
        self, ticker_id: int, symbol: str
    ) -> dict | None:
        """Get comprehensive context for trading signal generation — date-aware.

        Adds WHERE date <= self.as_of_date to all queries.
        52-week high/low computed relative to as_of_date (not date.today()).
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

    # ------------------------------------------------------------------
    # Override 4: _store_analysis — writes to backtest_analyses (NOT ai_analyses)
    # ------------------------------------------------------------------

    async def _store_analysis(
        self,
        ticker_id: int,
        analysis_type,
        analysis_date: date,
        signal: str,
        score: int,
        reasoning: str,
        raw_response: dict | None,
    ) -> None:
        """Store analysis result into backtest_analyses with upsert.

        CRITICAL: Writes to backtest_analyses (never ai_analyses).
        Uses self.as_of_date as analysis_date (ignoring the parent's date.today()).
        analysis_type stored as plain string (column is VARCHAR, no CAST needed).
        """
        from sqlalchemy import text

        # Extract string value from AnalysisType enum if needed
        atype_str = analysis_type.value if hasattr(analysis_type, "value") else str(analysis_type)
        raw_json = json.dumps(raw_response) if raw_response else None

        await self.session.execute(
            text("""
                INSERT INTO backtest_analyses
                    (run_id, ticker_id, analysis_type, analysis_date, signal, score, reasoning, model_version, raw_response)
                VALUES
                    (:run_id, :tid, :atype, :adate, :signal, :score, :reasoning, :model, CAST(:raw AS jsonb))
                ON CONFLICT ON CONSTRAINT uq_backtest_analyses_run_ticker_type_date
                DO UPDATE SET
                    signal = :signal,
                    score = :score,
                    reasoning = :reasoning,
                    model_version = :model,
                    raw_response = CAST(:raw AS jsonb)
            """),
            {
                "run_id": self.run_id,
                "tid": ticker_id,
                "atype": atype_str,
                "adate": self.as_of_date,  # Use as_of_date, NOT the passed analysis_date
                "signal": signal,
                "score": score,
                "reasoning": reasoning,
                "model": self.model,
                "raw": raw_json,
            },
        )
