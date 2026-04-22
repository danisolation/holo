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
    TradingSignalBatchResponse,  # Phase 19
    TickerTradingSignal,         # Phase 19 — for post-validation typing
)
from app.services.gemini_usage_service import GeminiUsageService
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
    AnalysisType.TRADING_SIGNAL: 0.2,  # Phase 19 — same as combined (balanced creativity)
}

# System instructions (D-09-01, D-09-03, D-09-05)
TECHNICAL_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích kỹ thuật chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, đánh giá: signal (strong_buy/buy/neutral/sell/strong_sell), "
    "strength (1-10), reasoning (2-3 câu tiếng Việt). "
    "Xem xét vùng RSI (quá bán <30 = tích cực, quá mua >70 = tiêu cực), "
    "giao cắt MACD, vị trí giá so với đường trung bình động, "
    "và vị trí Bollinger Band.\n\n" + SCORING_RUBRIC
)

FUNDAMENTAL_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích cơ bản chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, đánh giá: health (strong/good/neutral/weak/critical), "
    "score (1-10), reasoning (2-3 câu tiếng Việt). "
    "Xem xét P/E so với trung bình thị trường VN (~12-15), khả năng sinh lời (ROE, ROA), "
    "tốc độ tăng trưởng, và ổn định tài chính (hệ số thanh toán, nợ/vốn).\n\n"
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
TECHNICAL_FEW_SHOT = """Ví dụ phân tích:

--- VNM ---
RSI(14) 5 phiên gần nhất: [42.1, 44.3, 46.8, 49.2, 52.1]
Vùng RSI: trung tính
MACD histogram 5 phiên: [-0.12, -0.05, 0.03, 0.11, 0.18]
Giao cắt MACD: tăng
SMA(20): 82000, SMA(50): 80500, SMA(200): 78000

Kết quả mẫu:
{"ticker": "VNM", "signal": "buy", "strength": 7, "reasoning": "RSI tăng dần từ vùng trung tính kết hợp MACD giao cắt tăng. Giá nằm trên tất cả đường trung bình động chính, xác nhận xu hướng tăng. Động lượng đang tích lũy nhưng chưa quá mua."}

Phân tích các mã sau dựa trên chỉ báo kỹ thuật 5 phiên gần nhất:"""

FUNDAMENTAL_FEW_SHOT = """Ví dụ phân tích:

--- VNM (Kỳ: Q4/2024) ---
P/E: 15.2, P/B: 3.1, EPS: 5000
ROE: 0.25, ROA: 0.12
Tăng trưởng doanh thu: 0.08, Tăng trưởng lợi nhuận: 0.05

Kết quả mẫu:
{"ticker": "VNM", "health": "good", "score": 7, "reasoning": "P/E 15.2 ở mức trung bình thị trường nhưng hợp lý nhờ ROE 25% cao. Tăng trưởng doanh thu và lợi nhuận ổn định dù không đột phá. Cấu trúc nợ thấp hỗ trợ sức khỏe tài chính tốt."}

Phân tích các mã sau dựa trên dữ liệu tài chính mới nhất:"""

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

# Phase 19: Trading Signal Pipeline Constants
TRADING_SIGNAL_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia giao dịch chứng khoán Việt Nam (HOSE/HNX/UPCOM). "
    "Cho mỗi mã, phân tích HAI hướng:\n"
    "1. LONG: Cơ hội mua vào (entry/SL/TP)\n"
    "2. BEARISH: Xu hướng GIẢM — khuyến nghị 'giảm vị thế' hoặc 'tránh mua' "
    "(KHÔNG phải bán khống — thị trường VN không cho phép retail short-sell)\n\n"
    "Quy tắc:\n"
    "- Entry trong khoảng ±5% giá hiện tại\n"
    "- Stop-loss trong phạm vi 2×ATR từ entry\n"
    "- Take-profit neo vào mức hỗ trợ/kháng cự hoặc Fibonacci\n"
    "- risk_reward_ratio = |TP1 - entry| / |entry - SL| (phải ≥ 0.5)\n"
    "- position_size_pct: % danh mục đề xuất (xem xét ATR và confidence)\n"
    "- timeframe: 'swing' (3-15 ngày) hoặc 'position' (nhiều tuần+)\n"
    "- reasoning: giải thích bằng tiếng Việt, tối đa 300 ký tự\n"
    "- recommended_direction: hướng có confidence cao hơn\n\n"
    + SCORING_RUBRIC
)

TRADING_SIGNAL_FEW_SHOT = """Ví dụ phân tích:

--- VNM ---
Giá hiện tại: 82,000 VND
ATR(14): 1,500 | ADX(14): 28.5 | RSI(14): 55.2
Stochastic %K: 62.1, %D: 58.3
Pivot: 81,500 | S1: 80,000 | S2: 78,500 | R1: 83,000 | R2: 84,500
Fib 23.6%: 80,800 | Fib 38.2%: 79,500 | Fib 50%: 78,500 | Fib 61.8%: 77,500
BB Upper: 84,200 | BB Middle: 81,800 | BB Lower: 79,400
52-week High: 90,000 | 52-week Low: 70,000

Kết quả mẫu:
{"ticker": "VNM", "recommended_direction": "long", "long_analysis": {"direction": "long", "confidence": 7, "trading_plan": {"entry_price": 82000, "stop_loss": 79500, "take_profit_1": 84500, "take_profit_2": 86000, "risk_reward_ratio": 1.0, "position_size_pct": 8, "timeframe": "swing"}, "reasoning": "RSI trung tính, ADX >25 cho thấy xu hướng rõ. Giá trên pivot, nhắm R1-R2."}, "bearish_analysis": {"direction": "bearish", "confidence": 4, "trading_plan": {"entry_price": 82000, "stop_loss": 84000, "take_profit_1": 80000, "take_profit_2": 78500, "risk_reward_ratio": 1.0, "position_size_pct": 3, "timeframe": "swing"}, "reasoning": "Xu hướng giảm yếu. Stochastic chưa overbought, chờ tín hiệu rõ hơn."}}

Phân tích các mã sau dựa trên dữ liệu kỹ thuật:"""


# Phase 19: Post-validation for trading signals (module-level — pure logic, no self)
def _validate_trading_signal(
    signal: "TickerTradingSignal",
    current_price: float,
    atr: float,
) -> tuple[bool, str]:
    """Validate a single ticker's trading signal against price/ATR bounds.

    Returns (is_valid, reason). Checks BOTH long and bearish analysis plans.
    Per CONTEXT.md: entry ±5% of current_price, SL within 3×ATR, TP within 5×ATR.
    """
    for analysis in [signal.long_analysis, signal.bearish_analysis]:
        plan = analysis.trading_plan
        # Entry within ±5% of current_price
        if current_price > 0 and abs(plan.entry_price - current_price) / current_price > 0.05:
            return False, f"Entry {plan.entry_price:.0f} outside ±5% of current {current_price:.0f}"
        # SL within 3×ATR of entry
        if atr > 0 and abs(plan.stop_loss - plan.entry_price) > 3 * atr:
            return False, f"SL {plan.stop_loss:.0f} exceeds 3×ATR ({3 * atr:.0f}) from entry {plan.entry_price:.0f}"
        # TP within 5×ATR of entry
        for tp in [plan.take_profit_1, plan.take_profit_2]:
            if atr > 0 and abs(tp - plan.entry_price) > 5 * atr:
                return False, f"TP {tp:.0f} exceeds 5×ATR ({5 * atr:.0f}) from entry {plan.entry_price:.0f}"
    return True, ""


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
            ctx = await self._get_trading_signal_context(tid, symbol)
            if ctx:
                ticker_data[symbol] = ctx
                ticker_ids[symbol] = tid

        logger.info(f"Trading signal context gathered: {len(ticker_data)}/{len(ticker_map)} tickers have data")

        if not ticker_data:
            return {"success": 0, "failed": 0, "failed_symbols": []}

        # Run batched analysis with reduced batch size
        return await self._run_batched_analysis(
            ticker_data, ticker_ids, AnalysisType.TRADING_SIGNAL,
            self._analyze_trading_signal_batch,
            batch_size_override=settings.trading_signal_batch_size,
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
                            ctx = ticker_data.get(symbol, {})
                            current_price = ctx.get("current_price", 0)
                            atr = ctx.get("atr_14", 0)
                            is_valid, reason = _validate_trading_signal(analysis, current_price, atr)

                            if is_valid:
                                signal = analysis.recommended_direction.value
                                score = (
                                    analysis.long_analysis.confidence
                                    if analysis.recommended_direction.value == "long"
                                    else analysis.bearish_analysis.confidence
                                )
                            else:
                                logger.warning(f"Trading signal validation failed for {symbol}: {reason}")
                                signal = "invalid"
                                score = 0
                        else:
                            signal = "unknown"
                            score = 5

                        # Extract reasoning based on analysis type
                        if analysis_type == AnalysisType.COMBINED:
                            reasoning = analysis.explanation
                        elif analysis_type == AnalysisType.TRADING_SIGNAL:
                            if signal != "invalid":
                                reasoning = (
                                    analysis.long_analysis.reasoning
                                    if analysis.recommended_direction.value == "long"
                                    else analysis.bearish_analysis.reasoning
                                )
                            else:
                                reasoning = f"Validation failed: {reason}"
                        else:
                            reasoning = analysis.reasoning

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
    # Gemini API Calls
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=4, max=15),
        retry=retry_if_exception_type(ServerError),
        reraise=True,
    )
    async def _call_gemini_with_retry(
        self, prompt: str, response_schema, temperature: float = 0.2,
        system_instruction: str | None = None,
        *, max_output_tokens: int = 16384, thinking_budget: int | None = None,
    ):
        """Internal: Gemini call with tenacity retry. Circuit breaker wraps this."""
        # For thinking models (2.5-flash), set thinking budget to prevent
        # internal reasoning from consuming the entire output token budget
        thinking_config = None
        if "2.5" in self.model:
            thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget or 1024)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                thinking_config=thinking_config,
            ),
        )
        return response

    async def _call_gemini(self, prompt: str, response_schema, temperature: float = 0.2, system_instruction: str | None = None, **kwargs):
        """Call Gemini API with circuit breaker protection.

        Circuit breaker wraps OUTSIDE tenacity (Pitfall 1):
        - tenacity retries 2x on ServerError
        - If all retries fail, that counts as 1 circuit breaker failure
        - After 3 such sequences, circuit opens
        """
        return await gemini_breaker.call(self._call_gemini_with_retry, prompt, response_schema, temperature, system_instruction, **kwargs)

    async def _record_usage(self, analysis_type: str, batch_size: int, response) -> None:
        """Record Gemini token usage after a successful API call."""
        try:
            usage_svc = GeminiUsageService(self.session)
            await usage_svc.record_usage(
                analysis_type=analysis_type,
                batch_size=batch_size,
                usage_metadata=getattr(response, "usage_metadata", None),
                model_name=self.model,
            )
        except Exception as e:
            # Usage tracking should never break analysis
            logger.warning(f"Failed to record Gemini usage: {e}")

    async def _analyze_technical_batch(
        self, ticker_data: dict[str, dict]
    ) -> TechnicalBatchResponse | None:
        """Analyze a batch of tickers for technical signals."""
        prompt = self._build_technical_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.TECHNICAL]
        sys_instr = TECHNICAL_SYSTEM_INSTRUCTION

        response = await self._call_gemini(prompt, TechnicalBatchResponse, temp, sys_instr)
        if response.usage_metadata:
            logger.debug(
                f"Gemini technical tokens: {response.usage_metadata.total_token_count}"
            )
        await self._record_usage("technical", len(ticker_data), response)
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
        if response.usage_metadata:
            logger.debug(
                f"Gemini fundamental tokens: {response.usage_metadata.total_token_count}"
            )
        await self._record_usage("fundamental", len(ticker_data), response)
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
        if response.usage_metadata:
            logger.debug(
                f"Gemini sentiment tokens: {response.usage_metadata.total_token_count}"
            )
        await self._record_usage("sentiment", len(ticker_data), response)
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
        if response.usage_metadata:
            logger.debug(
                f"Gemini combined tokens: {response.usage_metadata.total_token_count}"
            )
        await self._record_usage("combined", len(ticker_data), response)
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

    async def _analyze_trading_signal_batch(
        self, ticker_data: dict[str, dict]
    ) -> TradingSignalBatchResponse | None:
        """Analyze a batch of tickers for dual-direction trading signals.

        Phase 19: Uses increased token budgets (32768 output, 2048 thinking).
        Follows same retry pattern as existing batch analyzers.
        """
        prompt = self._build_trading_signal_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.TRADING_SIGNAL]
        sys_instr = TRADING_SIGNAL_SYSTEM_INSTRUCTION

        response = await self._call_gemini(
            prompt, TradingSignalBatchResponse, temp, sys_instr,
            max_output_tokens=settings.trading_signal_max_tokens,
            thinking_budget=settings.trading_signal_thinking_budget,
        )
        if response.usage_metadata:
            logger.debug(
                f"Gemini trading_signal tokens: {response.usage_metadata.total_token_count}"
            )
        await self._record_usage("trading_signal", len(ticker_data), response)
        result = response.parsed

        if result is None and response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(
                prompt, TradingSignalBatchResponse, 0.05, sys_instr,
                max_output_tokens=settings.trading_signal_max_tokens,
                thinking_budget=settings.trading_signal_thinking_budget,
            )
            result = response.parsed

        if result is None and response.text:
            logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = TradingSignalBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
                logger.debug(f"Raw response text: {response.text[:500]}")
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

    async def _get_trading_signal_context(
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
        from sqlalchemy import func as sa_func
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
            lines.append(f"RSI(14) 5 phiên gần nhất: {data['rsi_14']}")
            lines.append(f"Vùng RSI: {data['rsi_zone']}")
            lines.append(f"MACD line 5 phiên: {data['macd_line']}")
            lines.append(f"MACD signal 5 phiên: {data['macd_signal']}")
            lines.append(f"MACD histogram 5 phiên: {data['macd_histogram']}")
            lines.append(f"Giao cắt MACD: {data['macd_crossover']}")
            lines.append(f"SMA(20): {data['sma_20']}, SMA(50): {data['sma_50']}, SMA(200): {data['sma_200']}")
            lines.append(f"EMA(12): {data['ema_12']}, EMA(26): {data['ema_26']}")
            lines.append(f"Bollinger Bands — Trên: {data['bb_upper']}, Giữa: {data['bb_middle']}, Dưới: {data['bb_lower']}")
            if "latest_close" in data:
                lines.append(f"Giá đóng cửa gần nhất: {data['latest_close']:,.0f} VND")
            if "price_vs_sma_20_pct" in data:
                lines.append(
                    f"Giá vs SMA(20): {data['price_vs_sma_20_pct']:+.1f}%, "
                    f"Giá vs SMA(50): {data.get('price_vs_sma_50_pct', 'N/A')}%, "
                    f"Giá vs SMA(200): {data.get('price_vs_sma_200_pct', 'N/A')}%"
                )

        return "\n".join(lines)

    def _build_fundamental_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build prompt for fundamental analysis batch."""
        lines = [
            FUNDAMENTAL_FEW_SHOT,
            "",
        ]

        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} (Kỳ: {data['period']}) ---")
            lines.append(f"P/E: {data['pe']}, P/B: {data['pb']}, EPS: {data['eps']}")
            lines.append(f"ROE: {data['roe']}, ROA: {data['roa']}")
            lines.append(f"Tăng trưởng doanh thu: {data['revenue_growth']}, Tăng trưởng lợi nhuận: {data['profit_growth']}")
            lines.append(f"Hệ số thanh toán: {data['current_ratio']}, Nợ/Vốn: {data['debt_to_equity']}")

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

    def _build_trading_signal_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build Vietnamese prompt for trading signal analysis batch.

        Phase 19: Includes ATR, ADX, RSI, Stochastic, S/R levels, Fibonacci,
        Bollinger Bands, 52-week high/low, and current price per ticker.
        """
        lines = [
            TRADING_SIGNAL_FEW_SHOT,
            "",
        ]
        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} ---")
            lines.append(f"Giá hiện tại: {data['current_price']:,.0f} VND")
            lines.append(
                f"ATR(14): {data.get('atr_14', 'N/A')} | "
                f"ADX(14): {data.get('adx_14', 'N/A')} | "
                f"RSI(14): {data.get('rsi_14', 'N/A')}"
            )
            lines.append(
                f"Stochastic %K: {data.get('stoch_k_14', 'N/A')}, "
                f"%D: {data.get('stoch_d_14', 'N/A')}"
            )
            lines.append(
                f"Pivot: {data.get('pivot_point', 'N/A')} | "
                f"S1: {data.get('support_1', 'N/A')} | "
                f"S2: {data.get('support_2', 'N/A')} | "
                f"R1: {data.get('resistance_1', 'N/A')} | "
                f"R2: {data.get('resistance_2', 'N/A')}"
            )
            lines.append(
                f"Fib 23.6%: {data.get('fib_236', 'N/A')} | "
                f"Fib 38.2%: {data.get('fib_382', 'N/A')} | "
                f"Fib 50%: {data.get('fib_500', 'N/A')} | "
                f"Fib 61.8%: {data.get('fib_618', 'N/A')}"
            )
            lines.append(
                f"BB Upper: {data.get('bb_upper', 'N/A')} | "
                f"BB Middle: {data.get('bb_middle', 'N/A')} | "
                f"BB Lower: {data.get('bb_lower', 'N/A')}"
            )
            if "week_52_high" in data:
                lines.append(
                    f"52-week High: {data['week_52_high']:,.0f} | "
                    f"52-week Low: {data['week_52_low']:,.0f}"
                )
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
