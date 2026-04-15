"""AI-powered analysis service using Google Gemini.

Sends batched ticker data to Gemini for technical and fundamental scoring.
Uses structured output (response_schema) for type-safe responses.

Key decisions (from CONTEXT.md):
- gemini-2.0-flash model, 15 RPM free tier
- Batch 10 tickers per prompt, 4-second delay between calls
- Retry 3x with exponential backoff (tenacity)
- Failed batches logged and skipped — partial analysis > none
- Technical input: 5-day indicator values, price vs MAs, MACD crossover state, RSI zone
- Fundamental input: P/E, P/B, ROE, ROA, revenue/profit growth, D/E, current ratio
"""
import asyncio
import json
from datetime import date
from decimal import Decimal

import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.financial import Financial
from app.models.technical_indicator import TechnicalIndicator
from app.schemas.analysis import TechnicalBatchResponse, FundamentalBatchResponse
from app.services.ticker_service import TickerService


class AIAnalysisService:
    """Gemini-powered analysis for technical and fundamental scoring."""

    def __init__(self, session: AsyncSession, api_key: str | None = None):
        self.session = session
        key = api_key or settings.gemini_api_key
        if not key:
            raise ValueError(
                "GEMINI_API_KEY is required. Set in .env or pass api_key parameter."
            )
        self.client = genai.Client(api_key=key)
        self.model = settings.gemini_model
        self.batch_size = settings.gemini_batch_size
        self.delay = settings.gemini_delay_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_all_tickers(self, analysis_type: str = "both") -> dict:
        """Run AI analysis for all active tickers.

        Args:
            analysis_type: 'technical', 'fundamental', or 'both'

        Returns: {technical: {success, failed, failed_symbols},
                  fundamental: {success, failed, failed_symbols}}
        """
        results: dict = {}

        if analysis_type in ("technical", "both"):
            results["technical"] = await self.run_technical_analysis()

        if analysis_type in ("fundamental", "both"):
            results["fundamental"] = await self.run_fundamental_analysis()

        return results

    async def run_technical_analysis(self) -> dict:
        """Technical analysis for all tickers.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        ticker_service = TickerService(self.session)
        ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting technical analysis for {len(ticker_map)} tickers")

        # Gather technical context for each ticker
        ticker_data: dict[str, dict] = {}
        ticker_ids: dict[str, int] = {}

        for symbol, ticker_id in ticker_map.items():
            context = await self._get_technical_context(ticker_id, symbol)
            if context is not None:
                ticker_data[symbol] = context
                ticker_ids[symbol] = ticker_id

        logger.info(
            f"Technical context gathered: {len(ticker_data)} tickers with indicator data"
        )

        if not ticker_data:
            logger.warning("No tickers with technical indicator data — skipping analysis")
            return {"success": 0, "failed": 0, "failed_symbols": []}

        return await self._run_batched_analysis(
            ticker_data=ticker_data,
            ticker_ids=ticker_ids,
            analysis_type=AnalysisType.TECHNICAL,
            batch_analyzer=self._analyze_technical_batch,
        )

    async def run_fundamental_analysis(self) -> dict:
        """Fundamental analysis for all tickers.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        ticker_service = TickerService(self.session)
        ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting fundamental analysis for {len(ticker_map)} tickers")

        # Gather fundamental context for each ticker
        ticker_data: dict[str, dict] = {}
        ticker_ids: dict[str, int] = {}

        for symbol, ticker_id in ticker_map.items():
            context = await self._get_fundamental_context(ticker_id, symbol)
            if context is not None:
                ticker_data[symbol] = context
                ticker_ids[symbol] = ticker_id

        logger.info(
            f"Fundamental context gathered: {len(ticker_data)} tickers with financial data"
        )

        if not ticker_data:
            logger.warning("No tickers with financial data — skipping analysis")
            return {"success": 0, "failed": 0, "failed_symbols": []}

        return await self._run_batched_analysis(
            ticker_data=ticker_data,
            ticker_ids=ticker_ids,
            analysis_type=AnalysisType.FUNDAMENTAL,
            batch_analyzer=self._analyze_fundamental_batch,
        )

    # ------------------------------------------------------------------
    # Batching & Orchestration
    # ------------------------------------------------------------------

    async def _run_batched_analysis(
        self,
        ticker_data: dict[str, dict],
        ticker_ids: dict[str, int],
        analysis_type: AnalysisType,
        batch_analyzer,
    ) -> dict:
        """Run analysis in batches with rate limiting.

        Batches tickers into groups of self.batch_size, calls Gemini per batch,
        stores results, and sleeps self.delay seconds between batches.
        """
        symbols = list(ticker_data.keys())
        success = 0
        failed = 0
        failed_symbols: list[str] = []
        today = date.today()

        total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(0, len(symbols), self.batch_size):
            batch_symbols = symbols[batch_idx : batch_idx + self.batch_size]
            batch_num = batch_idx // self.batch_size + 1
            batch_data = {s: ticker_data[s] for s in batch_symbols}

            logger.info(
                f"Analyzing batch {batch_num}/{total_batches} "
                f"({len(batch_symbols)} tickers): {batch_symbols}"
            )

            try:
                result = await batch_analyzer(batch_data)

                if result is None:
                    logger.error(f"Batch {batch_num}: Gemini returned None — skipping")
                    failed += len(batch_symbols)
                    failed_symbols.extend(batch_symbols)
                    continue

                # Store each ticker's analysis
                for analysis in result.analyses:
                    symbol = analysis.ticker
                    tid = ticker_ids.get(symbol)
                    if tid is None:
                        logger.warning(f"Gemini returned unknown ticker: {symbol}")
                        continue

                    # Extract signal and score based on analysis type
                    if analysis_type == AnalysisType.TECHNICAL:
                        signal = analysis.signal.value
                        score = analysis.strength
                    else:
                        signal = analysis.health.value
                        score = analysis.score

                    await self._store_analysis(
                        ticker_id=tid,
                        analysis_type=analysis_type,
                        analysis_date=today,
                        signal=signal,
                        score=score,
                        reasoning=analysis.reasoning,
                        raw_response=analysis.model_dump(),
                    )
                    success += 1

                await self.session.commit()

            except Exception as e:
                logger.error(
                    f"Batch {batch_num} failed after retries — "
                    f"{type(e).__name__}: {e}"
                )
                failed += len(batch_symbols)
                failed_symbols.extend(batch_symbols)

            # Rate limiting: delay between batches (except after last batch)
            if batch_idx + self.batch_size < len(symbols):
                await asyncio.sleep(self.delay)

        result_dict = {
            "success": success,
            "failed": failed,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"{analysis_type.value} analysis complete: {result_dict}")
        return result_dict

    # ------------------------------------------------------------------
    # Gemini API Calls
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(settings.gemini_max_retries),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((ClientError, ServerError)),
        reraise=True,
    )
    async def _call_gemini(self, prompt: str, response_schema):
        """Call Gemini with retry on rate limit / server errors.

        CRITICAL: Uses client.aio.models (async), NOT client.models (sync).
        Sync blocks FastAPI's event loop.
        """
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.2,  # Low for consistent analysis
                max_output_tokens=4096,
            ),
        )
        return response

    async def _analyze_technical_batch(
        self, ticker_data: dict[str, dict]
    ) -> TechnicalBatchResponse | None:
        """Analyze a batch of tickers for technical signals."""
        prompt = self._build_technical_prompt(ticker_data)
        response = await self._call_gemini(prompt, TechnicalBatchResponse)
        logger.debug(
            f"Gemini technical tokens: {response.usage_metadata.total_token_count}"
        )
        return response.parsed

    async def _analyze_fundamental_batch(
        self, ticker_data: dict[str, dict]
    ) -> FundamentalBatchResponse | None:
        """Analyze a batch of tickers for fundamental health."""
        prompt = self._build_fundamental_prompt(ticker_data)
        response = await self._call_gemini(prompt, FundamentalBatchResponse)
        logger.debug(
            f"Gemini fundamental tokens: {response.usage_metadata.total_token_count}"
        )
        return response.parsed

    # ------------------------------------------------------------------
    # Context Gathering
    # ------------------------------------------------------------------

    async def _get_technical_context(
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

        return context

    async def _get_fundamental_context(
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

    # ------------------------------------------------------------------
    # Prompt Builders
    # ------------------------------------------------------------------

    def _build_technical_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build prompt for technical analysis batch."""
        lines = [
            "You are a Vietnamese stock market (HOSE) technical analyst. "
            "Analyze the following tickers based on their technical indicators "
            "from the last 5 trading days.",
            "",
            "For each ticker, provide:",
            "- signal: one of strong_buy, buy, neutral, sell, strong_sell",
            "- strength: 1-10 (confidence in the signal)",
            "- reasoning: brief explanation (2-3 sentences in English)",
            "",
            "Consider RSI zones (oversold <30 = bullish, overbought >70 = bearish), "
            "MACD crossovers, price position relative to moving averages, "
            "and Bollinger Band positions.",
            "",
            "Tickers:",
        ]

        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} ---")
            lines.append(f"RSI(14) last 5 days: {data['rsi_14']}")
            lines.append(f"RSI zone: {data['rsi_zone']}")
            lines.append(f"MACD line last 5 days: {data['macd_line']}")
            lines.append(f"MACD signal last 5 days: {data['macd_signal']}")
            lines.append(f"MACD histogram last 5 days: {data['macd_histogram']}")
            lines.append(f"MACD crossover: {data['macd_crossover']}")
            lines.append(f"SMA(20): {data['sma_20']}, SMA(50): {data['sma_50']}, SMA(200): {data['sma_200']}")
            lines.append(f"EMA(12): {data['ema_12']}, EMA(26): {data['ema_26']}")
            lines.append(f"Bollinger Bands — Upper: {data['bb_upper']}, Middle: {data['bb_middle']}, Lower: {data['bb_lower']}")

        return "\n".join(lines)

    def _build_fundamental_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build prompt for fundamental analysis batch."""
        lines = [
            "You are a Vietnamese stock market (HOSE) fundamental analyst. "
            "Evaluate the financial health of the following tickers based on "
            "their most recent financial data.",
            "",
            "For each ticker, provide:",
            "- health: one of strong, good, neutral, weak, critical",
            "- score: 1-10 (overall financial health score)",
            "- reasoning: brief explanation (2-3 sentences in English)",
            "",
            "Consider P/E relative to sector averages (Vietnam market P/E ~12-15), "
            "profitability (ROE, ROA), growth rates, and financial stability "
            "(current ratio, debt-to-equity).",
            "",
            "Tickers:",
        ]

        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} (Period: {data['period']}) ---")
            lines.append(f"P/E: {data['pe']}, P/B: {data['pb']}, EPS: {data['eps']}")
            lines.append(f"ROE: {data['roe']}, ROA: {data['roa']}")
            lines.append(f"Revenue Growth: {data['revenue_growth']}, Profit Growth: {data['profit_growth']}")
            lines.append(f"Current Ratio: {data['current_ratio']}, Debt/Equity: {data['debt_to_equity']}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    async def _store_analysis(
        self,
        ticker_id: int,
        analysis_type: AnalysisType,
        analysis_date: date,
        signal: str,
        score: int,
        reasoning: str,
        raw_response: dict | None,
    ) -> None:
        """Store analysis result with upsert (INSERT ... ON CONFLICT DO UPDATE)."""
        stmt = insert(AIAnalysis).values(
            ticker_id=ticker_id,
            analysis_type=analysis_type,
            analysis_date=analysis_date,
            signal=signal,
            score=score,
            reasoning=reasoning,
            model_version=self.model,
            raw_response=raw_response,
        ).on_conflict_do_update(
            constraint="uq_ai_analyses_ticker_type_date",
            set_={
                "signal": signal,
                "score": score,
                "reasoning": reasoning,
                "model_version": self.model,
                "raw_response": raw_response,
            },
        )
        await self.session.execute(stmt)
