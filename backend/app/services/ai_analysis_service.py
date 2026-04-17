"""AI-powered analysis service using Google Gemini.

Sends batched ticker data to Gemini for technical, fundamental, sentiment,
and combined scoring. Uses structured output (response_schema) for type-safe responses.

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
import json
from datetime import date, datetime, timedelta
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
from app.models.daily_price import DailyPrice
from app.models.financial import Financial
from app.models.news_article import NewsArticle
from app.models.technical_indicator import TechnicalIndicator
from app.models.ticker import Ticker
from app.resilience import gemini_breaker
from app.schemas.analysis import (
    TechnicalBatchResponse,
    FundamentalBatchResponse,
    SentimentBatchResponse,
    CombinedBatchResponse,
)
from app.services.ticker_service import TickerService

# Module-level lock: serializes all Gemini API access across concurrent
# background tasks.  When multiple analysis types are triggered via separate
# POST endpoints they queue instead of competing for the rate limit.
_gemini_lock = asyncio.Lock()

# ------------------------------------------------------------------
# Phase 9 Constants: Prompt Architecture
# ------------------------------------------------------------------

SCORING_RUBRIC = """Scoring rubric (apply consistently):
- 1-2: Very weak signal / very negative outlook
- 3-4: Weak signal / slightly negative outlook
- 5-6: Moderate / neutral — no clear direction
- 7-8: Strong signal / positive outlook
- 9-10: Very strong signal / very positive outlook
Use the FULL range. Scores of 1-2 and 9-10 are valid for extreme cases."""

# Per-type temperatures (D-09-06)
ANALYSIS_TEMPERATURES: dict[AnalysisType, float] = {
    AnalysisType.TECHNICAL: 0.1,
    AnalysisType.FUNDAMENTAL: 0.2,
    AnalysisType.SENTIMENT: 0.3,
    AnalysisType.COMBINED: 0.2,
}

# System instructions (D-09-01, D-09-03, D-09-05)
TECHNICAL_SYSTEM_INSTRUCTION = (
    "You are a senior HOSE (Vietnam stock exchange) technical analyst. "
    "For each ticker, output: signal (strong_buy/buy/neutral/sell/strong_sell), "
    "strength (1-10), reasoning (2-3 sentences in English). "
    "Consider RSI zones (oversold <30 = bullish, overbought >70 = bearish), "
    "MACD crossovers, price position relative to moving averages, "
    "and Bollinger Band positions.\n\n" + SCORING_RUBRIC
)

FUNDAMENTAL_SYSTEM_INSTRUCTION = (
    "You are a senior HOSE (Vietnam stock exchange) fundamental analyst. "
    "For each ticker, output: health (strong/good/neutral/weak/critical), "
    "score (1-10), reasoning (2-3 sentences in English). "
    "Consider P/E relative to VN market average (~12-15), profitability (ROE, ROA), "
    "growth rates, and financial stability (current ratio, debt-to-equity).\n\n"
    + SCORING_RUBRIC
)

SENTIMENT_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích tâm lý thị trường chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, đánh giá: sentiment (very_positive/positive/neutral/negative/very_negative), "
    "score (1-10), reasoning (2-3 câu tiếng Việt). "
    "Nếu không có tin tức, sentiment = neutral, score = 5.\n\n" + SCORING_RUBRIC
)

COMBINED_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, cung cấp: recommendation (mua/ban/giu), confidence (1-10), "
    "explanation (tiếng Việt, tối đa 200 từ). "
    "Quy tắc confidence: 8-10 = cả 3 chiều đồng thuận; 5-7 = 2/3 đồng thuận; "
    "1-4 = tín hiệu mâu thuẫn hoặc thiếu dữ liệu.\n\n" + SCORING_RUBRIC
)

# Few-shot examples (D-09-02)
TECHNICAL_FEW_SHOT = """Example analysis:

--- VNM ---
RSI(14) last 5 days: [42.1, 44.3, 46.8, 49.2, 52.1]
RSI zone: neutral
MACD histogram last 5 days: [-0.12, -0.05, 0.03, 0.11, 0.18]
MACD crossover: bullish
SMA(20): 82000, SMA(50): 80500, SMA(200): 78000

Expected output:
{"ticker": "VNM", "signal": "buy", "strength": 7, "reasoning": "RSI rising from mid-range with bullish MACD crossover. Price above all major moving averages confirms uptrend. Momentum building but not yet overbought."}

Now analyze the following tickers based on their technical indicators from the last 5 trading days:"""

FUNDAMENTAL_FEW_SHOT = """Example analysis:

--- VNM (Period: Q4/2024) ---
P/E: 15.2, P/B: 3.1, EPS: 5000
ROE: 0.25, ROA: 0.12
Revenue Growth: 0.08, Profit Growth: 0.05

Expected output:
{"ticker": "VNM", "health": "good", "score": 7, "reasoning": "P/E of 15.2 is at market average but justified by strong ROE of 25%. Modest but stable growth in revenue and profit. Low debt profile supports financial health."}

Now analyze the following tickers based on their most recent financial data:"""

SENTIMENT_FEW_SHOT = """Ví dụ phân tích:

--- HPG (3 tin tức) ---
1. Hòa Phát đặt mục tiêu sản lượng thép kỷ lục năm 2025
2. HPG báo lãi quý 4 tăng 35% so với cùng kỳ
3. Giá thép xây dựng tăng mạnh, lợi cho Hòa Phát

Kết quả mẫu:
{"ticker": "HPG", "sentiment": "positive", "score": 7, "reasoning": "Tin tức tích cực với mục tiêu sản lượng mới và lãi tăng mạnh. Giá thép tăng hỗ trợ triển vọng kinh doanh."}

Phân tích các mã cổ phiếu sau:"""

COMBINED_FEW_SHOT = """Ví dụ phân tích:

--- VNM ---
Kỹ thuật: signal=buy, strength=7
Cơ bản: health=good, score=8
Tâm lý: sentiment=positive, score=7

Kết quả mẫu:
{"ticker": "VNM", "recommendation": "mua", "confidence": 8, "explanation": "Cả 3 chiều phân tích đều tích cực. Kỹ thuật cho tín hiệu mua với MACD bullish crossover. Cơ bản vững chắc với ROE 25% và tăng trưởng ổn định. Tâm lý thị trường tích cực với tin tốt về doanh thu. Khuyến nghị mua với độ tin cậy cao."}

Đưa ra khuyến nghị tổng hợp cho các mã sau:"""


class AIAnalysisService:
    """Gemini-powered analysis for technical, fundamental, sentiment, and combined scoring."""

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

    async def analyze_all_tickers(self, analysis_type: str = "both", ticker_filter: dict[str, int] | None = None) -> dict:
        """Run AI analysis for all active tickers.

        Acquires a module-level lock so that concurrent triggers (from separate
        POST endpoints) queue up instead of competing for the Gemini rate limit.

        Args:
            analysis_type: 'technical', 'fundamental', 'sentiment', 'combined',
                           'both' (tech+fund only for backward compat), or 'all' (all 4 types)
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

        ticker_data: dict[str, dict] = {}
        ticker_ids: dict[str, int] = {}

        for symbol, ticker_id in ticker_map.items():
            context = await self._get_sentiment_context(ticker_id, symbol)
            ticker_data[symbol] = context
            ticker_ids[symbol] = ticker_id

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
            batch_analyzer=self._analyze_sentiment_batch,
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
            context = await self._get_combined_context(ticker_id, symbol)
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
            batch_analyzer=self._analyze_combined_batch,
        )

    async def analyze_watchlisted_tickers(
        self, exchanges: list[str], max_extra: int = 50
    ) -> dict:
        """Analyze only watchlisted tickers from given exchanges.

        Per CONTEXT.md: HNX/UPCOM tickers get AI analysis only if in
        the UserWatchlist (Telegram /watch). Capped at max_extra per day
        to stay within Gemini 1500 RPD budget.

        Args:
            exchanges: List of exchanges to query (e.g., ["HNX", "UPCOM"])
            max_extra: Maximum tickers to analyze (default 50)

        Returns: {analyzed: int, skipped: int, exchanges: list[str]}
        """
        from app.models.user_watchlist import UserWatchlist

        # Query active tickers in target exchanges that are in watchlist
        stmt = (
            select(Ticker.symbol, Ticker.id)
            .join(UserWatchlist, UserWatchlist.ticker_id == Ticker.id)
            .where(Ticker.exchange.in_(exchanges), Ticker.is_active == True)
        )
        result = await self.session.execute(stmt)
        watchlisted = {row[0]: row[1] for row in result.fetchall()}

        # Cap at max_extra
        symbols_to_analyze = list(watchlisted.keys())[:max_extra]
        skipped = len(watchlisted) - len(symbols_to_analyze)

        if not symbols_to_analyze:
            logger.info(f"No watchlisted tickers in {exchanges} — skipping analysis")
            return {"analyzed": 0, "skipped": 0, "exchanges": exchanges}

        logger.info(
            f"Analyzing {len(symbols_to_analyze)} watchlisted tickers "
            f"from {exchanges} (capped at {max_extra}, skipped {skipped})"
        )

        # Run analysis for selected tickers using existing batch method
        ticker_id_map = {s: watchlisted[s] for s in symbols_to_analyze}
        for analysis_type in ["technical", "fundamental"]:
            try:
                await self.analyze_all_tickers(
                    analysis_type=analysis_type,
                    ticker_filter=ticker_id_map,
                )
            except Exception as e:
                logger.error(f"Failed {analysis_type} analysis for watchlisted: {e}")

        return {
            "analyzed": len(symbols_to_analyze),
            "skipped": skipped,
            "exchanges": exchanges,
        }

    async def analyze_single_ticker(self, ticker_id: int, symbol: str) -> dict:
        """Run all analysis types for a single ticker (on-demand).

        Used by the 'Analyze now' endpoint for HNX/UPCOM tickers
        not in the daily schedule.

        Acquires the Gemini lock once for all 4 analysis types to avoid
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
    ) -> dict:
        """Run analysis in batches with rate limiting.

        Batches tickers into groups of self.batch_size, calls Gemini per batch,
        stores results, and sleeps self.delay seconds between batches.
        Handles 429 quota errors by waiting the specified retry delay.
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
                        elif analysis_type == AnalysisType.FUNDAMENTAL:
                            signal = analysis.health.value
                            score = analysis.score
                        elif analysis_type == AnalysisType.SENTIMENT:
                            signal = analysis.sentiment.value
                            score = analysis.score
                        elif analysis_type == AnalysisType.COMBINED:
                            signal = analysis.recommendation.value
                            score = analysis.confidence
                        else:
                            signal = "unknown"
                            score = 5

                        # Combined uses explanation field; others use reasoning
                        reasoning = (
                            analysis.explanation
                            if analysis_type == AnalysisType.COMBINED
                            else analysis.reasoning
                        )

                        await self._store_analysis(
                            ticker_id=tid,
                            analysis_type=analysis_type,
                            analysis_date=today,
                            signal=signal,
                            score=score,
                            reasoning=reasoning,
                            raw_response=analysis.model_dump(),
                        )
                        success += 1

                    await self.session.commit()
                    break  # Success — exit retry loop

                except ClientError as e:
                    error_str = str(e)
                    if "429" in error_str and attempt < max_retries:
                        # Parse retry delay from error message
                        import re
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
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=4, max=15),
        retry=retry_if_exception_type(ServerError),
        reraise=True,
    )
    async def _call_gemini_with_retry(self, prompt: str, response_schema, temperature: float = 0.2, system_instruction: str | None = None):
        """Internal: Gemini call with tenacity retry. Circuit breaker wraps this."""
        # For thinking models (2.5-flash), set thinking budget to prevent
        # internal reasoning from consuming the entire output token budget
        thinking_config = None
        if "2.5" in self.model:
            thinking_config = types.ThinkingConfig(thinking_budget=1024)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=temperature,
                max_output_tokens=16384,
                thinking_config=thinking_config,
            ),
        )
        return response

    async def _call_gemini(self, prompt: str, response_schema, temperature: float = 0.2, system_instruction: str | None = None):
        """Call Gemini API with circuit breaker protection.

        Circuit breaker wraps OUTSIDE tenacity (Pitfall 1):
        - tenacity retries 2x on ServerError
        - If all retries fail, that counts as 1 circuit breaker failure
        - After 3 such sequences, circuit opens
        """
        return await gemini_breaker.call(self._call_gemini_with_retry, prompt, response_schema, temperature, system_instruction)

    async def _analyze_technical_batch(
        self, ticker_data: dict[str, dict]
    ) -> TechnicalBatchResponse | None:
        """Analyze a batch of tickers for technical signals."""
        prompt = self._build_technical_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.TECHNICAL]
        sys_instr = TECHNICAL_SYSTEM_INSTRUCTION

        response = await self._call_gemini(prompt, TechnicalBatchResponse, temp, sys_instr)
        logger.debug(
            f"Gemini technical tokens: {response.usage_metadata.total_token_count}"
        )
        result = response.parsed

        if result is None and response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(prompt, TechnicalBatchResponse, 0.05, sys_instr)
            result = response.parsed

        if result is None and response.text:
            logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = TechnicalBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
                logger.debug(f"Raw response text: {response.text[:500]}")
        return result

    async def _analyze_fundamental_batch(
        self, ticker_data: dict[str, dict]
    ) -> FundamentalBatchResponse | None:
        """Analyze a batch of tickers for fundamental health."""
        prompt = self._build_fundamental_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.FUNDAMENTAL]
        sys_instr = FUNDAMENTAL_SYSTEM_INSTRUCTION

        response = await self._call_gemini(prompt, FundamentalBatchResponse, temp, sys_instr)
        logger.debug(
            f"Gemini fundamental tokens: {response.usage_metadata.total_token_count}"
        )
        result = response.parsed

        if result is None and response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(prompt, FundamentalBatchResponse, 0.05, sys_instr)
            result = response.parsed

        if result is None and response.text:
            logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = FundamentalBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
        return result

    async def _analyze_sentiment_batch(
        self, ticker_data: dict[str, dict]
    ) -> SentimentBatchResponse | None:
        """Analyze a batch of tickers for sentiment from news titles."""
        prompt = self._build_sentiment_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.SENTIMENT]
        sys_instr = SENTIMENT_SYSTEM_INSTRUCTION

        response = await self._call_gemini(prompt, SentimentBatchResponse, temp, sys_instr)
        logger.debug(
            f"Gemini sentiment tokens: {response.usage_metadata.total_token_count}"
        )
        result = response.parsed

        if result is None and response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(prompt, SentimentBatchResponse, 0.05, sys_instr)
            result = response.parsed

        if result is None and response.text:
            logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = SentimentBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
        return result

    async def _analyze_combined_batch(
        self, ticker_data: dict[str, dict]
    ) -> CombinedBatchResponse | None:
        """Analyze a batch of tickers for combined recommendation."""
        prompt = self._build_combined_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.COMBINED]
        sys_instr = COMBINED_SYSTEM_INSTRUCTION

        response = await self._call_gemini(prompt, CombinedBatchResponse, temp, sys_instr)
        logger.debug(
            f"Gemini combined tokens: {response.usage_metadata.total_token_count}"
        )
        result = response.parsed

        if result is None and response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(prompt, CombinedBatchResponse, 0.05, sys_instr)
            result = response.parsed

        if result is None and response.text:
            logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = CombinedBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
        return result

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

    async def _get_sentiment_context(
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
        titles = [row[0] for row in result.all()]

        return {
            "news_titles": titles,
            "news_count": len(titles),
        }

    async def _get_combined_context(
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

    # ------------------------------------------------------------------
    # Prompt Builders
    # ------------------------------------------------------------------

    def _build_technical_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build prompt for technical analysis batch."""
        lines = [
            TECHNICAL_FEW_SHOT,
            "",
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
            if "latest_close" in data:
                lines.append(f"Latest close: {data['latest_close']:,.0f} VND")
            if "price_vs_sma_20_pct" in data:
                lines.append(
                    f"Price vs SMA(20): {data['price_vs_sma_20_pct']:+.1f}%, "
                    f"Price vs SMA(50): {data.get('price_vs_sma_50_pct', 'N/A')}%, "
                    f"Price vs SMA(200): {data.get('price_vs_sma_200_pct', 'N/A')}%"
                )

        return "\n".join(lines)

    def _build_fundamental_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build prompt for fundamental analysis batch."""
        lines = [
            FUNDAMENTAL_FEW_SHOT,
            "",
        ]

        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} (Period: {data['period']}) ---")
            lines.append(f"P/E: {data['pe']}, P/B: {data['pb']}, EPS: {data['eps']}")
            lines.append(f"ROE: {data['roe']}, ROA: {data['roa']}")
            lines.append(f"Revenue Growth: {data['revenue_growth']}, Profit Growth: {data['profit_growth']}")
            lines.append(f"Current Ratio: {data['current_ratio']}, Debt/Equity: {data['debt_to_equity']}")

        return "\n".join(lines)

    def _build_sentiment_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build Vietnamese prompt for sentiment analysis batch.

        Per CONTEXT.md: Feed Vietnamese titles directly to Gemini (no translation).
        Per CONTEXT.md: Batch 10 tickers per call.
        """
        lines = [
            SENTIMENT_FEW_SHOT,
            "",
        ]

        for symbol, data in ticker_data.items():
            news_titles = data.get("news_titles", [])
            lines.append(f"\n--- {symbol} ({len(news_titles)} tin tức) ---")
            if news_titles:
                for i, title in enumerate(news_titles, 1):
                    lines.append(f"{i}. {title}")
            else:
                lines.append("Không có tin tức gần đây.")

        return "\n".join(lines)

    def _build_combined_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build Vietnamese prompt for combined recommendation batch.

        Per CONTEXT.md: Single Gemini call combining tech + fund + sentiment.
        Per CONTEXT.md: Gemini reasons across all dimensions (NOT a weighted formula).
        Per CONTEXT.md: Confidence based on signal alignment, data freshness, news volume.
        Per CONTEXT.md: Vietnamese explanation, max ~200 words, natural language.
        """
        lines = [
            COMBINED_FEW_SHOT,
            "",
        ]

        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} ---")
            lines.append(f"Kỹ thuật: signal={data.get('tech_signal', 'N/A')}, strength={data.get('tech_score', 'N/A')}")
            lines.append(f"Cơ bản: health={data.get('fund_signal', 'N/A')}, score={data.get('fund_score', 'N/A')}")
            lines.append(f"Tâm lý: sentiment={data.get('sent_signal', 'neutral')}, score={data.get('sent_score', 5)}")

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
        """Store analysis result with upsert (INSERT ... ON CONFLICT DO UPDATE).

        Uses raw SQL to avoid SQLAlchemy Enum serialization issues with asyncpg.
        """
        from sqlalchemy import text
        raw_json = json.dumps(raw_response) if raw_response else None
        await self.session.execute(
            text("""
                INSERT INTO ai_analyses (ticker_id, analysis_type, analysis_date, signal, score, reasoning, model_version, raw_response)
                VALUES (:tid, CAST(:atype AS analysis_type), :adate, :signal, :score, :reasoning, :model, CAST(:raw AS jsonb))
                ON CONFLICT ON CONSTRAINT uq_ai_analyses_ticker_type_date
                DO UPDATE SET signal = :signal, score = :score, reasoning = :reasoning,
                              model_version = :model, raw_response = CAST(:raw AS jsonb)
            """),
            {
                "tid": ticker_id,
                "atype": analysis_type.value,
                "adate": analysis_date,
                "signal": signal,
                "score": score,
                "reasoning": reasoning,
                "model": self.model,
                "raw": raw_json,
            },
        )
