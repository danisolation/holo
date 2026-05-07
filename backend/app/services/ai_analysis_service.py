"""AI-powered analysis service using Google Gemini.

Sends batched ticker data to Gemini for technical, fundamental, sentiment,
and combined scoring. Uses structured output (response_schema) for type-safe responses.

Orchestration layer — composes ContextBuilder + GeminiClient + AnalysisStorage.

Key decisions (from CONTEXT.md):
- gemini-2.0-flash model, 15 RPM free tier
- Batch 10 tickers per prompt, 4-second delay between calls
- Retry 3x with exponential backoff (tenacity)
- Failed batches logged and skipped — partial analysis > none
- Technical input: 5-day indicator values, price vs MAs, MACD crossover state, RSI zone
- Fundamental input: P/E, P/B, ROE, ROA, revenue/profit growth, D/E, current ratio
- Sentiment input: Vietnamese news titles from CafeF (no translation per CONTEXT.md)
- Combined: Gemini reasons across all 3 dimensions (NOT a weighted formula)
"""
import asyncio
import re
from datetime import date

import google.genai as genai
from google.genai.errors import ClientError, ServerError
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_analysis import AnalysisType
from app.models.ticker import Ticker
from app.services.analysis.context_builder import ContextBuilder
from app.services.analysis.gemini_client import GeminiClient
from app.services.analysis.storage import AnalysisStorage
from app.services.ticker_service import TickerService

# Re-export from analysis.prompts for backward compatibility
from app.services.analysis.prompts import (  # noqa: F401
    SCORING_RUBRIC,
    ANALYSIS_TEMPERATURES,
    TECHNICAL_SYSTEM_INSTRUCTION,
    FUNDAMENTAL_SYSTEM_INSTRUCTION,
    SENTIMENT_SYSTEM_INSTRUCTION,
    COMBINED_SYSTEM_INSTRUCTION,
    TRADING_SIGNAL_SYSTEM_INSTRUCTION,
    UNIFIED_SYSTEM_INSTRUCTION,
    TECHNICAL_FEW_SHOT,
    FUNDAMENTAL_FEW_SHOT,
    SENTIMENT_FEW_SHOT,
    COMBINED_FEW_SHOT,
    TRADING_SIGNAL_FEW_SHOT,
    UNIFIED_FEW_SHOT,
    _validate_trading_signal,
    _validate_unified_signal,
)

# Module-level lock: serializes all Gemini API access across concurrent
# background tasks.  When multiple analysis types are triggered via separate
# POST endpoints they queue instead of competing for the rate limit.
_gemini_lock = asyncio.Lock()


class AIAnalysisService:
    """Gemini-powered analysis for technical, fundamental, sentiment, and combined scoring.

    Composes ContextBuilder (DB queries), GeminiClient (API calls + prompt building),
    and AnalysisStorage (DB upsert). Public API and batching logic stay here.
    """

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

        # Composed modules
        self.context_builder = ContextBuilder(session)
        self.gemini_client = GeminiClient(session, self.client, self.model)
        self.storage = AnalysisStorage(session, self.model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_all_tickers(self, analysis_type: str = "both", ticker_filter: dict[str, int] | None = None) -> dict:
        """Run AI analysis for all active tickers.

        Acquires a module-level lock so that concurrent triggers (from separate
        POST endpoints) queue up instead of competing for the Gemini rate limit.

        Args:
            analysis_type: 'technical', 'fundamental', 'sentiment', 'combined',
                           'trading_signal', 'both' (tech+fund only for backward compat),
                           or 'all' (all 5 types)
            ticker_filter: Optional dict of {symbol: ticker_id} to analyze only specific tickers.
                          When provided, bypasses get_ticker_id_map() call.

        Returns: dict with results per analysis type run
        """
        logger.info(
            f"analyze_all_tickers({analysis_type}) — waiting for Gemini lock…"
        )
        async with _gemini_lock:
            logger.info(
                f"analyze_all_tickers({analysis_type}) — lock acquired, starting"
            )
            results: dict = {}

            if analysis_type in ("technical", "both", "all"):
                results["technical"] = await self.run_technical_analysis(ticker_filter=ticker_filter)

            if analysis_type in ("fundamental", "both", "all"):
                results["fundamental"] = await self.run_fundamental_analysis(ticker_filter=ticker_filter)

            if analysis_type in ("sentiment", "all"):
                results["sentiment"] = await self.run_sentiment_analysis(ticker_filter=ticker_filter)

            if analysis_type in ("combined", "all"):
                results["combined"] = await self.run_combined_analysis(ticker_filter=ticker_filter)

            if analysis_type in ("trading_signal", "all"):
                results["trading_signal"] = await self.run_trading_signal_analysis(ticker_filter=ticker_filter)

            if analysis_type in ("unified", "all"):
                results["unified"] = await self.run_unified_analysis(ticker_filter=ticker_filter)

            return results

    async def run_technical_analysis(self, ticker_filter: dict[str, int] | None = None) -> dict:
        """Technical analysis for all tickers.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        if ticker_filter is not None:
            ticker_map = ticker_filter
        else:
            ticker_service = TickerService(self.session)
            ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting technical analysis for {len(ticker_map)} tickers")

        # Gather technical context for all tickers in batch
        ticker_data = await self.context_builder.batch_get_technical_contexts(ticker_map)
        ticker_ids = {s: ticker_map[s] for s in ticker_data}

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
            batch_analyzer=self.gemini_client.analyze_technical_batch,
        )

    async def run_fundamental_analysis(self, ticker_filter: dict[str, int] | None = None) -> dict:
        """Fundamental analysis for all tickers.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        if ticker_filter is not None:
            ticker_map = ticker_filter
        else:
            ticker_service = TickerService(self.session)
            ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting fundamental analysis for {len(ticker_map)} tickers")

        # Gather fundamental context for all tickers in batch
        ticker_data = await self.context_builder.batch_get_fundamental_contexts(ticker_map)
        ticker_ids = {s: ticker_map[s] for s in ticker_data}

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
            batch_analyzer=self.gemini_client.analyze_fundamental_batch,
        )

    async def run_sentiment_analysis(self, ticker_filter: dict[str, int] | None = None) -> dict:
        """Sentiment analysis for all tickers based on recent news.

        Feeds Vietnamese news titles to Gemini (no translation per CONTEXT.md).
        Tickers with 0 news articles are included with empty list — Gemini
        will score them as neutral per the prompt instruction.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        if ticker_filter is not None:
            ticker_map = ticker_filter
        else:
            ticker_service = TickerService(self.session)
            ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting sentiment analysis for {len(ticker_map)} tickers")

        # Gather sentiment context for all tickers in batch
        ticker_data = await self.context_builder.batch_get_sentiment_contexts(ticker_map)
        ticker_ids = {s: ticker_map[s] for s in ticker_data}

        logger.info(
            f"Sentiment context gathered: {len(ticker_data)} tickers "
            f"({sum(1 for d in ticker_data.values() if d['news_titles'])} with news)"
        )

        if not ticker_data:
            return {"success": 0, "failed": 0, "failed_symbols": []}

        return await self._run_batched_analysis(
            ticker_data=ticker_data,
            ticker_ids=ticker_ids,
            analysis_type=AnalysisType.SENTIMENT,
            batch_analyzer=self.gemini_client.analyze_sentiment_batch,
        )

    async def run_combined_analysis(self, ticker_filter: dict[str, int] | None = None) -> dict:
        """Combined 3-dimensional recommendation for all tickers.

        Reads latest technical, fundamental, and sentiment analyses from ai_analyses table.
        Produces holistic mua/bán/giữ recommendation with confidence and Vietnamese explanation.
        Per CONTEXT.md: Gemini reasons across all dimensions (NOT a weighted formula).

        Graceful degradation per CONTEXT.md: if sentiment is missing, combine with tech+fund only.
        Skips tickers that have neither technical nor fundamental analysis.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        if ticker_filter is not None:
            ticker_map = ticker_filter
        else:
            ticker_service = TickerService(self.session)
            ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting combined analysis for {len(ticker_map)} tickers")

        ticker_data: dict[str, dict] = {}
        ticker_ids: dict[str, int] = {}
        skipped = 0

        for symbol, ticker_id in ticker_map.items():
            context = await self.context_builder.get_combined_context(ticker_id, symbol)
            if context is not None:
                ticker_data[symbol] = context
                ticker_ids[symbol] = ticker_id
            else:
                skipped += 1

        logger.info(
            f"Combined context gathered: {len(ticker_data)} tickers with data, {skipped} skipped (no prior analysis)"
        )

        if not ticker_data:
            logger.warning("No tickers with prior analysis data — skipping combined analysis")
            return {"success": 0, "failed": 0, "failed_symbols": []}

        return await self._run_batched_analysis(
            ticker_data=ticker_data,
            ticker_ids=ticker_ids,
            analysis_type=AnalysisType.COMBINED,
            batch_analyzer=self.gemini_client.analyze_combined_batch,
        )

    async def run_trading_signal_analysis(self, ticker_filter: dict[str, int] | None = None) -> dict:
        """Trading signal analysis for all tickers.

        Phase 19: Generates dual-direction (LONG + BEARISH) trading plans.
        Uses reduced batch size (15) and increased token budgets.
        Post-validates signals against price/ATR bounds.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        if ticker_filter is not None:
            ticker_map = ticker_filter
        else:
            ticker_svc = TickerService(self.session)
            ticker_map = await ticker_svc.get_ticker_id_map()

        logger.info(f"Starting trading signal analysis for {len(ticker_map)} tickers")

        # Gather context (includes ATR for post-validation)
        ticker_data: dict[str, dict] = {}
        ticker_ids: dict[str, int] = {}

        for symbol, tid in ticker_map.items():
            ctx = await self.context_builder.get_trading_signal_context(tid, symbol)
            if ctx:
                ticker_data[symbol] = ctx
                ticker_ids[symbol] = tid

        logger.info(f"Trading signal context gathered: {len(ticker_data)}/{len(ticker_map)} tickers have data")

        if not ticker_data:
            return {"success": 0, "failed": 0, "failed_symbols": []}

        # Run batched analysis with reduced batch size
        return await self._run_batched_analysis(
            ticker_data, ticker_ids, AnalysisType.TRADING_SIGNAL,
            self.gemini_client.analyze_trading_signal_batch,
            batch_size_override=settings.trading_signal_batch_size,
        )

    async def run_unified_analysis(self, ticker_filter: dict[str, int] | None = None) -> dict:
        """Unified analysis for all tickers — Phase 88 / v19.0.

        Single Gemini prompt receives ALL data (indicators, financials, news, rumors)
        and outputs one coherent analysis per ticker with signal + entry/SL/TP.
        Replaces the 5-type pipeline with one unified call.

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        if ticker_filter is not None:
            ticker_map = ticker_filter
        else:
            ticker_svc = TickerService(self.session)
            ticker_map = await ticker_svc.get_ticker_id_map()

        logger.info(f"Starting unified analysis for {len(ticker_map)} tickers")

        # Gather comprehensive context per ticker
        ticker_data: dict[str, dict] = {}
        ticker_ids: dict[str, int] = {}

        for symbol, tid in ticker_map.items():
            ctx = await self.context_builder.get_unified_context(tid, symbol)
            if ctx:
                ticker_data[symbol] = ctx
                ticker_ids[symbol] = tid

        logger.info(f"Unified context gathered: {len(ticker_data)}/{len(ticker_map)} tickers have data")

        if not ticker_data:
            return {"success": 0, "failed": 0, "failed_symbols": []}

        # Run batched analysis with unified batch size
        return await self._run_batched_analysis(
            ticker_data, ticker_ids, AnalysisType.UNIFIED,
            self.gemini_client.analyze_unified_batch,
            batch_size_override=settings.unified_batch_size,
        )

    async def analyze_single_ticker(self, ticker_id: int, symbol: str) -> dict:
        """Run all analysis types for a single ticker (on-demand).

        Used by the 'Analyze now' endpoint for HNX/UPCOM tickers
        not in the daily schedule.

        Acquires the Gemini lock once for all 5 analysis types to avoid
        starvation — without this, the daily pipeline (400+ tickers) could
        grab the lock between each type, delaying on-demand results for hours.
        """
        logger.info(f"On-demand analysis for {symbol} (id={ticker_id})")
        ticker_filter = {symbol: ticker_id}
        results = {}
        async with _gemini_lock:
            for analysis_type, runner in [
                ("technical", self.run_technical_analysis),
                ("fundamental", self.run_fundamental_analysis),
                ("sentiment", self.run_sentiment_analysis),
                ("combined", self.run_combined_analysis),
                ("trading_signal", self.run_trading_signal_analysis),  # Phase 19
                ("unified", self.run_unified_analysis),  # Phase 88 / v19.0
            ]:
                try:
                    results[analysis_type] = await runner(ticker_filter=ticker_filter)
                except Exception as e:
                    logger.error(f"On-demand {analysis_type} failed for {symbol}: {e}")
                    results[analysis_type] = {"error": str(e)}
        return results

    # ------------------------------------------------------------------
    # Batching & Orchestration
    # ------------------------------------------------------------------

    async def _run_batched_analysis(
        self,
        ticker_data: dict[str, dict],
        ticker_ids: dict[str, int],
        analysis_type: AnalysisType,
        batch_analyzer,
        batch_size_override: int | None = None,  # Phase 19: for trading_signal's 15-ticker batches
    ) -> dict:
        """Run analysis in batches with rate limiting.

        Batches tickers into groups of batch_size, calls Gemini per batch,
        stores results, and sleeps self.delay seconds between batches.
        Handles 429 quota errors by waiting the specified retry delay.
        """
        symbols = list(ticker_data.keys())
        batch_size = batch_size_override or self.batch_size
        success = 0
        failed = 0
        failed_symbols: list[str] = []
        today = date.today()

        total_batches = (len(symbols) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(symbols), batch_size):
            batch_symbols = symbols[batch_idx : batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            batch_data = {s: ticker_data[s] for s in batch_symbols}

            logger.info(
                f"Analyzing batch {batch_num}/{total_batches} "
                f"({len(batch_symbols)} tickers): {batch_symbols}"
            )

            # Retry loop for 429 rate limit errors
            max_retries = 5
            for attempt in range(max_retries + 1):
                try:
                    result = await batch_analyzer(batch_data)

                    if result is None:
                        logger.error(f"Batch {batch_num}: Gemini returned None — skipping")
                        failed += len(batch_symbols)
                        failed_symbols.extend(batch_symbols)
                        break

                    # Store each ticker's analysis
                    # Trading signals use 'signals' field; others use 'analyses'
                    items = result.signals if analysis_type == AnalysisType.TRADING_SIGNAL else result.analyses
                    for analysis in items:
                        symbol = analysis.ticker
                        tid = ticker_ids.get(symbol)
                        if tid is None:
                            logger.warning(f"Gemini returned unknown ticker: {symbol}")
                            continue

                        # Extract signal and score based on analysis type
                        if analysis_type == AnalysisType.TECHNICAL:
                            signal = analysis.signal.value
                            score = analysis.strength
                        elif analysis_type == AnalysisType.FUNDAMENTAL:
                            signal = analysis.health.value
                            score = analysis.score
                        elif analysis_type == AnalysisType.SENTIMENT:
                            signal = analysis.sentiment.value
                            score = analysis.score
                        elif analysis_type == AnalysisType.COMBINED:
                            signal = analysis.recommendation.value
                            score = analysis.confidence
                        elif analysis_type == AnalysisType.TRADING_SIGNAL:
                            # Post-validate trading signals against price/ATR bounds
                            # DB stores prices in nghìn đồng (x1000), Gemini outputs in VND
                            ctx = ticker_data.get(symbol, {})
                            current_price = ctx.get("current_price", 0) * 1000
                            atr = ctx.get("atr_14", 0) * 1000
                            w52_high = ctx.get("week_52_high")
                            w52_low = ctx.get("week_52_low")
                            is_valid, reason = _validate_trading_signal(
                                analysis, current_price, atr,
                                week_52_high=w52_high * 1000 if w52_high else None,
                                week_52_low=w52_low * 1000 if w52_low else None,
                            )

                            if is_valid:
                                signal = analysis.recommended_direction.value
                                score = analysis.confidence
                            else:
                                logger.warning(f"Trading signal validation failed for {symbol}: {reason}")
                                signal = "invalid"
                                score = 0
                        elif analysis_type == AnalysisType.UNIFIED:
                            # Post-validate unified analysis against price/ATR bounds
                            ctx = ticker_data.get(symbol, {})
                            current_price = ctx.get("current_price", 0) * 1000
                            atr = ctx.get("atr_14", 0) * 1000
                            w52_high = ctx.get("week_52_high")
                            w52_low = ctx.get("week_52_low")
                            is_valid, reason = _validate_unified_signal(
                                analysis, current_price, atr,
                                week_52_high=w52_high * 1000 if w52_high else None,
                                week_52_low=w52_low * 1000 if w52_low else None,
                            )

                            if is_valid:
                                signal = analysis.signal.value
                                score = analysis.score
                            else:
                                logger.warning(f"Unified analysis validation failed for {symbol}: {reason}")
                                signal = "invalid"
                                score = 0
                        else:
                            signal = "unknown"
                            score = 5

                        # Extract reasoning based on analysis type
                        if analysis_type == AnalysisType.COMBINED:
                            reasoning = (
                                f"## Tóm tắt\n{analysis.summary}\n\n"
                                f"## Mức giá quan trọng\n{analysis.key_levels}\n\n"
                                f"## Rủi ro\n{analysis.risks}\n\n"
                                f"## Hành động cụ thể\n{analysis.action}"
                            )
                        elif analysis_type == AnalysisType.TRADING_SIGNAL:
                            if signal != "invalid":
                                reasoning = analysis.reasoning
                            else:
                                reasoning = f"Validation failed: {reason}"
                        elif analysis_type == AnalysisType.UNIFIED:
                            if signal != "invalid":
                                reasoning = analysis.reasoning
                            else:
                                reasoning = f"Validation failed: {reason}"
                        else:
                            reasoning = analysis.reasoning

                        # Score-signal consistency (AIQ-01): low score cannot be bullish
                        BULLISH_SIGNALS = {
                            AnalysisType.TECHNICAL: {"strong_buy", "buy"},
                            AnalysisType.FUNDAMENTAL: {"strong", "good"},
                            AnalysisType.SENTIMENT: {"very_positive", "positive"},
                            AnalysisType.COMBINED: {"mua"},
                            AnalysisType.UNIFIED: {"mua"},
                        }
                        bullish_set = BULLISH_SIGNALS.get(analysis_type, set())
                        if score < 5 and signal in bullish_set:
                            corrected = {
                                AnalysisType.TECHNICAL: "neutral",
                                AnalysisType.FUNDAMENTAL: "neutral",
                                AnalysisType.SENTIMENT: "neutral",
                                AnalysisType.COMBINED: "giu",
                                AnalysisType.UNIFIED: "giu",
                            }.get(analysis_type, "neutral")
                            logger.warning(
                                f"Score-signal mismatch for {symbol} ({analysis_type.value}): "
                                f"score={score} with signal={signal} → corrected to {corrected}"
                            )
                            signal = corrected

                        # Prepare extra columns for unified analysis
                        extra_kwargs = {}
                        if analysis_type == AnalysisType.UNIFIED and signal != "invalid":
                            extra_kwargs = {
                                "entry_price": analysis.entry_price,
                                "stop_loss": analysis.stop_loss,
                                "take_profit_1": analysis.take_profit_1,
                                "take_profit_2": analysis.take_profit_2,
                                "key_levels": analysis.key_levels,
                            }

                        await self.storage.store_analysis(
                            ticker_id=tid,
                            analysis_type=analysis_type,
                            analysis_date=today,
                            signal=signal,
                            score=score,
                            reasoning=reasoning,
                            raw_response=analysis.model_dump(),
                            **extra_kwargs,
                        )
                        success += 1

                    await self.session.commit()
                    break  # Success — exit retry loop

                except ClientError as e:
                    error_str = str(e)
                    if "429" in error_str and attempt < max_retries:
                        # Parse retry delay from error message
                        match = re.search(r'retry in ([\d.]+)s', error_str)
                        wait_time = float(match.group(1)) + 5 if match else 60
                        logger.warning(
                            f"Batch {batch_num} hit 429 rate limit (attempt {attempt+1}/{max_retries}). "
                            f"Waiting {wait_time:.0f}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(
                        f"Batch {batch_num} failed — {type(e).__name__}: {e}"
                    )
                    await self.session.rollback()
                    failed += len(batch_symbols)
                    failed_symbols.extend(batch_symbols)
                    break

                except ServerError as e:
                    # 503 UNAVAILABLE = Gemini model overloaded — retryable
                    if attempt < max_retries:
                        wait_time = 30 * (attempt + 1)  # Progressive: 30s, 60s, 90s…
                        logger.warning(
                            f"Batch {batch_num} hit server error (attempt {attempt+1}/{max_retries}): {e}. "
                            f"Waiting {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(
                        f"Batch {batch_num} failed after {max_retries} server-error retries — {type(e).__name__}: {e}"
                    )
                    await self.session.rollback()
                    failed += len(batch_symbols)
                    failed_symbols.extend(batch_symbols)
                    break

                except Exception as e:
                    logger.error(
                        f"Batch {batch_num} failed — {type(e).__name__}: {e}"
                    )
                    await self.session.rollback()
                    failed += len(batch_symbols)
                    failed_symbols.extend(batch_symbols)
                    break

            # Rate limiting: delay between batches (except after last batch)
            if batch_idx + batch_size < len(symbols):
                await asyncio.sleep(self.delay)

        result_dict = {
            "success": success,
            "failed": failed,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"{analysis_type.value} analysis complete: {result_dict}")
        return result_dict

    # ------------------------------------------------------------------
    # Backward-compat forwarding methods (used by tests)
    # ------------------------------------------------------------------

    def _build_technical_prompt(self, ticker_data):
        return self.gemini_client.build_technical_prompt(ticker_data)

    def _build_fundamental_prompt(self, ticker_data):
        return self.gemini_client.build_fundamental_prompt(ticker_data)

    def _build_sentiment_prompt(self, ticker_data):
        return self.gemini_client.build_sentiment_prompt(ticker_data)

    def _build_combined_prompt(self, ticker_data):
        return self.gemini_client.build_combined_prompt(ticker_data)

    def _build_trading_signal_prompt(self, ticker_data):
        return self.gemini_client.build_trading_signal_prompt(ticker_data)

    async def _call_gemini_with_retry(self, *args, **kwargs):
        return await self.gemini_client._call_gemini_with_retry(*args, **kwargs)

    async def _call_gemini(self, *args, **kwargs):
        return await self.gemini_client._call_gemini(*args, **kwargs)

    async def _record_usage(self, *args, **kwargs):
        return await self.gemini_client._record_usage(*args, **kwargs)

    async def _get_technical_context(self, ticker_id, symbol):
        return await self.context_builder.get_technical_context(ticker_id, symbol)

    async def _get_fundamental_context(self, ticker_id, symbol):
        return await self.context_builder.get_fundamental_context(ticker_id, symbol)

    async def _get_sentiment_context(self, ticker_id, symbol):
        return await self.context_builder.get_sentiment_context(ticker_id, symbol)

    async def _get_combined_context(self, ticker_id, symbol):
        return await self.context_builder.get_combined_context(ticker_id, symbol)

    async def _get_trading_signal_context(self, ticker_id, symbol):
        return await self.context_builder.get_trading_signal_context(ticker_id, symbol)

    async def _store_analysis(self, **kwargs):
        return await self.storage.store_analysis(**kwargs)