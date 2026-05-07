"""Pydantic schemas for AI analysis.

These serve dual purpose:
1. Gemini response_schema — constrains LLM output to valid JSON
2. API response schemas — typed responses for analysis endpoints

Per RESEARCH.md: Gemini accepts Pydantic BaseModel classes directly
in GenerateContentConfig(response_schema=...) and returns validated
models via response.parsed.
"""
from enum import Enum
from pydantic import BaseModel, Field


# --- Technical Analysis Schemas ---

class TechnicalSignal(str, Enum):
    """Technical analysis signal levels."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TickerTechnicalAnalysis(BaseModel):
    """Single ticker technical analysis from Gemini."""
    ticker: str
    signal: TechnicalSignal
    strength: int = Field(ge=1, le=10, description="Signal strength 1-10")
    reasoning: str


class TechnicalBatchResponse(BaseModel):
    """Batch response for technical analysis (multiple tickers per Gemini call)."""
    analyses: list[TickerTechnicalAnalysis]


# --- Fundamental Analysis Schemas ---

class FundamentalHealth(str, Enum):
    """Fundamental health assessment levels."""
    STRONG = "strong"
    GOOD = "good"
    NEUTRAL = "neutral"
    WEAK = "weak"
    CRITICAL = "critical"


class TickerFundamentalAnalysis(BaseModel):
    """Single ticker fundamental analysis from Gemini."""
    ticker: str
    health: FundamentalHealth
    score: int = Field(ge=1, le=10, description="Health score 1-10")
    reasoning: str


class FundamentalBatchResponse(BaseModel):
    """Batch response for fundamental analysis (multiple tickers per Gemini call)."""
    analyses: list[TickerFundamentalAnalysis]


# --- Sentiment Analysis Schemas (Phase 3) ---

class SentimentLevel(str, Enum):
    """Sentiment assessment levels."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class TickerSentimentAnalysis(BaseModel):
    """Single ticker sentiment analysis from Gemini."""
    ticker: str
    sentiment: SentimentLevel
    score: int = Field(ge=1, le=10, description="Sentiment score 1-10 (1=very negative, 10=very positive)")
    reasoning: str


class SentimentBatchResponse(BaseModel):
    """Batch response for sentiment analysis (multiple tickers per Gemini call)."""
    analyses: list[TickerSentimentAnalysis]


# --- Combined Recommendation Schemas (Phase 3) ---

class Recommendation(str, Enum):
    """Combined recommendation (Vietnamese)."""
    MUA = "mua"   # buy
    BAN = "ban"   # sell
    GIU = "giu"   # hold


class TickerCombinedAnalysis(BaseModel):
    """Single ticker combined recommendation from Gemini."""
    ticker: str
    recommendation: Recommendation
    confidence: int = Field(ge=1, le=10, description="Confidence level 1-10")
    summary: str = Field(description="Tóm tắt: đánh giá tổng quan 3-5 câu tiếng Việt, tổng hợp cả 3 chiều phân tích")
    key_levels: str = Field(description="Mức giá quan trọng: hỗ trợ, kháng cự, entry gợi ý, stop-loss, take-profit")
    risks: str = Field(description="Rủi ro: 2-3 yếu tố rủi ro chính cần lưu ý (thị trường, ngành, nội tại)")
    action: str = Field(description="Hành động cụ thể: mua/bán/giữ tại mức giá nào, khối lượng, thời điểm")


class CombinedBatchResponse(BaseModel):
    """Batch response for combined recommendation (multiple tickers per Gemini call)."""
    analyses: list[TickerCombinedAnalysis]


# --- Trading Signal Schemas (Phase 19) ---

class Direction(str, Enum):
    """Trading signal direction. BEARISH = bearish outlook (NOT literal short-selling per VN market)."""
    LONG = "long"
    BEARISH = "bearish"


class Timeframe(str, Enum):
    """Trading timeframe. NO intraday/scalp — VN T+2.5 settlement."""
    SWING = "swing"        # 3-15 days
    POSITION = "position"  # weeks+


class TradingPlanDetail(BaseModel):
    """Concrete entry/SL/TP targets for one direction."""
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float = Field(ge=0.5)
    position_size_pct: int = Field(ge=1, le=100)
    timeframe: Timeframe


class DirectionAnalysis(BaseModel):
    """Analysis for one direction (LONG or BEARISH)."""
    direction: Direction
    confidence: int = Field(ge=1, le=10)
    trading_plan: TradingPlanDetail
    reasoning: str = Field(description="Vietnamese explanation, max 300 chars")


class TickerTradingSignal(BaseModel):
    """Single-direction trading signal for one ticker."""
    ticker: str
    recommended_direction: Direction
    confidence: int = Field(ge=1, le=10)
    trading_plan: TradingPlanDetail
    reasoning: str = Field(default="", description="Vietnamese explanation, max 300 chars")


class TradingSignalBatchResponse(BaseModel):
    """Batch response for trading signal analysis."""
    signals: list[TickerTradingSignal]


# --- Unified Analysis Schemas (Phase 88 / v19.0) ---

class UnifiedSignal(str, Enum):
    """Unified analysis signal (Vietnamese)."""
    MUA = "mua"    # buy
    BAN = "ban"    # sell
    GIU = "giu"    # hold


class UnifiedTimeframe(str, Enum):
    """Trading timeframe for unified analysis."""
    SWING = "swing"        # 3-15 days
    POSITION = "position"  # weeks+


class TickerUnifiedAnalysis(BaseModel):
    """Single ticker unified analysis — combines all dimensions into one output."""
    ticker: str
    signal: UnifiedSignal
    score: int = Field(ge=1, le=10, description="Confidence/strength score 1-10")
    entry_price: float = Field(description="Entry price in VND")
    stop_loss: float = Field(description="Stop-loss price in VND")
    take_profit_1: float = Field(description="Take-profit target 1 in VND")
    take_profit_2: float = Field(description="Take-profit target 2 in VND")
    risk_reward_ratio: float = Field(ge=0.3, description="Risk/reward ratio")
    position_size_pct: int = Field(ge=1, le=100, description="% of portfolio suggested")
    timeframe: UnifiedTimeframe
    key_levels: str = Field(description="Key support/resistance levels explanation")
    reasoning: str = Field(description="Multi-dimensional reasoning in Vietnamese (min 200 chars)")


class UnifiedBatchResponse(BaseModel):
    """Batch response for unified analysis (multiple tickers per Gemini call)."""
    analyses: list[TickerUnifiedAnalysis]


# --- API Response Schemas ---

class AnalysisResultResponse(BaseModel):
    """API response for a single analysis result."""
    ticker_symbol: str
    analysis_type: str
    analysis_date: str
    signal: str
    score: int
    reasoning: str
    model_version: str
    raw_response: dict | None = None  # Phase 20: full structured data for trading signals


class AnalysisTriggerResponse(BaseModel):
    """API response for analysis trigger endpoints."""
    message: str
    triggered: bool


class IndicatorResponse(BaseModel):
    """API response for indicator data."""
    ticker_symbol: str
    date: str
    rsi_14: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    # Phase 17: Volatility, Trend Strength, Momentum
    atr_14: float | None = None
    adx_14: float | None = None
    plus_di_14: float | None = None
    minus_di_14: float | None = None
    stoch_k_14: float | None = None
    stoch_d_14: float | None = None
    # Phase 18: Support & Resistance
    pivot_point: float | None = None
    support_1: float | None = None
    support_2: float | None = None
    resistance_1: float | None = None
    resistance_2: float | None = None
    fib_236: float | None = None
    fib_382: float | None = None
    fib_500: float | None = None
    fib_618: float | None = None


class NewsArticleResponse(BaseModel):
    """API response for a single news article."""
    title: str
    url: str
    published_at: str


class SummaryResponse(BaseModel):
    """API response for full analysis summary (all dimensions)."""
    ticker_symbol: str
    technical: AnalysisResultResponse | None = None
    fundamental: AnalysisResultResponse | None = None
    sentiment: AnalysisResultResponse | None = None
    combined: AnalysisResultResponse | None = None
    trading_signal: AnalysisResultResponse | None = None  # Phase 19
