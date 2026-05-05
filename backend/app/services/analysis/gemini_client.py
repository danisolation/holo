"""Gemini API client — calls, retries, batch analyzers, and prompt builders.

Extracted from AIAnalysisService: _call_gemini*, _record_usage,
_analyze_*_batch, and _build_*_prompt methods.
"""
import json

from google.genai import types
from google.genai.errors import ServerError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models.ai_analysis import AnalysisType
from app.resilience import gemini_breaker
from app.schemas.analysis import (
    TechnicalBatchResponse,
    FundamentalBatchResponse,
    SentimentBatchResponse,
    CombinedBatchResponse,
    TradingSignalBatchResponse,
)
from app.services.analysis.prompts import (
    ANALYSIS_TEMPERATURES,
    TECHNICAL_SYSTEM_INSTRUCTION,
    FUNDAMENTAL_SYSTEM_INSTRUCTION,
    SENTIMENT_SYSTEM_INSTRUCTION,
    COMBINED_SYSTEM_INSTRUCTION,
    TRADING_SIGNAL_SYSTEM_INSTRUCTION,
    TECHNICAL_FEW_SHOT,
    FUNDAMENTAL_FEW_SHOT,
    SENTIMENT_FEW_SHOT,
    COMBINED_FEW_SHOT,
    TRADING_SIGNAL_FEW_SHOT,
)
from app.services.gemini_usage_service import GeminiUsageService


class GeminiClient:
    """Wraps Gemini API calls, batch analyzers, and prompt builders."""

    def __init__(self, session: AsyncSession, client, model: str):
        self.session = session
        self.client = client
        self.model = model

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

    # ------------------------------------------------------------------
    # Batch Analyzers
    # ------------------------------------------------------------------

    async def analyze_technical_batch(
        self, ticker_data: dict[str, dict]
    ) -> TechnicalBatchResponse | None:
        """Analyze a batch of tickers for technical signals."""
        prompt = self.build_technical_prompt(ticker_data)
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

    async def analyze_fundamental_batch(
        self, ticker_data: dict[str, dict]
    ) -> FundamentalBatchResponse | None:
        """Analyze a batch of tickers for fundamental health."""
        prompt = self.build_fundamental_prompt(ticker_data)
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

    async def analyze_sentiment_batch(
        self, ticker_data: dict[str, dict]
    ) -> SentimentBatchResponse | None:
        """Analyze a batch of tickers for sentiment from news titles."""
        prompt = self.build_sentiment_prompt(ticker_data)
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

    async def analyze_combined_batch(
        self, ticker_data: dict[str, dict]
    ) -> CombinedBatchResponse | None:
        """Analyze a batch of tickers for combined recommendation."""
        prompt = self.build_combined_prompt(ticker_data)
        temp = ANALYSIS_TEMPERATURES[AnalysisType.COMBINED]
        sys_instr = COMBINED_SYSTEM_INSTRUCTION

        response = await self._call_gemini(
            prompt, CombinedBatchResponse, temp, sys_instr,
            max_output_tokens=settings.combined_max_tokens,
            thinking_budget=settings.combined_thinking_budget,
        )
        if response.usage_metadata:
            logger.debug(
                f"Gemini combined tokens: {response.usage_metadata.total_token_count}"
            )
        await self._record_usage("combined", len(ticker_data), response)
        result = response.parsed

        if result is None and response.text:
            logger.warning("response.parsed is None, retrying at temperature=0.05")
            response = await self._call_gemini(
                prompt, CombinedBatchResponse, 0.05, sys_instr,
                max_output_tokens=settings.combined_max_tokens,
                thinking_budget=settings.combined_thinking_budget,
            )
            result = response.parsed

        if result is None and response.text:
            logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                result = CombinedBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")
        return result

    async def analyze_trading_signal_batch(
        self, ticker_data: dict[str, dict]
    ) -> TradingSignalBatchResponse | None:
        """Analyze a batch of tickers for dual-direction trading signals.

        Phase 19: Uses increased token budgets (32768 output, 2048 thinking).
        Follows same retry pattern as existing batch analyzers.
        """
        prompt = self.build_trading_signal_prompt(ticker_data)
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
    # Prompt Builders
    # ------------------------------------------------------------------

    def build_technical_prompt(self, ticker_data: dict[str, dict]) -> str:
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
            # Phase 67: Volume profile (CTX-01)
            if "avg_volume_20d" in data:
                lines.append(
                    f"KL trung bình 20 phiên: {data['avg_volume_20d']:,}, "
                    f"KL mới nhất: {data.get('latest_volume', 'N/A'):,}, "
                    f"Tỷ lệ KL: {data.get('relative_volume', 'N/A')}x"
                )
            if "volume_trend" in data:
                lines.append(
                    f"Xu hướng KL: {data['volume_trend']} ({data.get('volume_change_pct', 0):+.1f}%)"
                )

        return "\n".join(lines)

    def build_fundamental_prompt(self, ticker_data: dict[str, dict]) -> str:
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

    def build_sentiment_prompt(self, ticker_data: dict[str, dict]) -> str:
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

    def build_combined_prompt(self, ticker_data: dict[str, dict]) -> str:
        """Build Vietnamese prompt for combined recommendation batch.

        Per CONTEXT.md: Single Gemini call combining tech + fund + sentiment.
        Per CONTEXT.md: Gemini reasons across all dimensions (NOT a weighted formula).
        Includes per-type reasoning text for richer context.
        """
        lines = [
            COMBINED_FEW_SHOT,
            "",
        ]

        for symbol, data in ticker_data.items():
            lines.append(f"\n--- {symbol} ---")
            lines.append(f"Kỹ thuật: signal={data.get('tech_signal', 'N/A')}, strength={data.get('tech_score', 'N/A')}")
            if data.get('tech_reasoning'):
                lines.append(f"  Chi tiết kỹ thuật: {data['tech_reasoning']}")
            lines.append(f"Cơ bản: health={data.get('fund_signal', 'N/A')}, score={data.get('fund_score', 'N/A')}")
            if data.get('fund_reasoning'):
                lines.append(f"  Chi tiết cơ bản: {data['fund_reasoning']}")
            lines.append(f"Tâm lý: sentiment={data.get('sent_signal', 'neutral')}, score={data.get('sent_score', 5)}")
            if data.get('sent_reasoning'):
                lines.append(f"  Chi tiết tâm lý: {data['sent_reasoning']}")
            # Phase 64: Rumor intelligence section (AIUP-01)
            if data.get('rumor_direction'):
                lines.append(
                    f"Tin đồn: hướng={data['rumor_direction']}, "
                    f"tin cậy={data.get('rumor_credibility', 'N/A')}/10, "
                    f"tác động={data.get('rumor_impact', 'N/A')}/10"
                )
                if data.get('rumor_key_claims'):
                    claims = data['rumor_key_claims'][:3]  # Top 3 claims
                    lines.append(f"  Thông tin chính: {'; '.join(claims)}")
                if data.get('rumor_reasoning'):
                    lines.append(f"  Phân tích tin đồn: {data['rumor_reasoning'][:200]}")
            # Phase 67: Sector peer comparison (CTX-02)
            if data.get('sector_avg_score') is not None:
                lines.append(
                    f"So sánh ngành ({data.get('sector', '')}): "
                    f"điểm trung bình ngành={data['sector_avg_score']}/10"
                )

        return "\n".join(lines)

    def build_trading_signal_prompt(self, ticker_data: dict[str, dict]) -> str:
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
                # Phase 67: Price percentile (CTX-03)
                if "price_percentile_52w" in data:
                    lines.append(f"Vị trí giá 52 tuần: {data['price_percentile_52w']:.0f}%")
            # Phase 67: Volume-price alignment (CTX-03)
            if "volume_price_alignment" in data:
                lines.append(f"KL-Giá tương quan: {data['volume_price_alignment']}")
            # Phase 64: Rumor context for trading signals (AIUP-02)
            if data.get("rumor_direction"):
                claims = data.get("rumor_key_claims", [])[:2]
                claims_str = "; ".join(claims) if claims else "không rõ"
                lines.append(
                    f"Tin đồn: {data['rumor_direction']} "
                    f"(tác động={data.get('rumor_impact', 'N/A')}/10) — {claims_str}"
                )
        return "\n".join(lines)
