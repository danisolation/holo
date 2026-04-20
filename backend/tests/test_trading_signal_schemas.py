"""Unit tests for trading signal Pydantic schemas (Phase 19).

Tests Direction/Timeframe enums, TradingPlanDetail bounds,
DirectionAnalysis confidence bounds, and full nested structure.
All tests are pure Pydantic validation — no DB, no async.
"""
import pytest
from pydantic import ValidationError


# ---- Enum tests ----

def test_direction_enum_values():
    """Direction enum has exactly 'long' and 'bearish'. No 'short'."""
    from app.schemas.analysis import Direction

    values = [d.value for d in Direction]
    assert "long" in values
    assert "bearish" in values
    assert len(values) == 2
    assert "short" not in values


def test_timeframe_enum_values():
    """Timeframe enum has exactly 'swing' and 'position'."""
    from app.schemas.analysis import Timeframe

    values = [t.value for t in Timeframe]
    assert "swing" in values
    assert "position" in values
    assert len(values) == 2


# ---- TradingPlanDetail tests ----

def _make_plan(**overrides):
    """Helper: build a valid TradingPlanDetail dict, with optional overrides."""
    from app.schemas.analysis import Timeframe

    defaults = dict(
        entry_price=25.0,
        stop_loss=23.5,
        take_profit_1=27.0,
        take_profit_2=29.0,
        risk_reward_ratio=1.5,
        position_size_pct=10,
        timeframe=Timeframe.SWING,
    )
    defaults.update(overrides)
    return defaults


def test_trading_plan_detail_valid():
    """Construct valid TradingPlanDetail, assert all fields accessible."""
    from app.schemas.analysis import TradingPlanDetail

    plan = TradingPlanDetail(**_make_plan())
    assert plan.entry_price == 25.0
    assert plan.stop_loss == 23.5
    assert plan.take_profit_1 == 27.0
    assert plan.take_profit_2 == 29.0
    assert plan.risk_reward_ratio == 1.5
    assert plan.position_size_pct == 10


def test_trading_plan_detail_rr_ratio_min():
    """risk_reward_ratio < 0.5 raises ValidationError."""
    from app.schemas.analysis import TradingPlanDetail

    with pytest.raises(ValidationError):
        TradingPlanDetail(**_make_plan(risk_reward_ratio=0.4))


def test_trading_plan_detail_position_size_bounds():
    """position_size_pct must be 1-100 inclusive."""
    from app.schemas.analysis import TradingPlanDetail

    with pytest.raises(ValidationError):
        TradingPlanDetail(**_make_plan(position_size_pct=0))

    with pytest.raises(ValidationError):
        TradingPlanDetail(**_make_plan(position_size_pct=101))

    # Boundary values are valid
    plan_1 = TradingPlanDetail(**_make_plan(position_size_pct=1))
    assert plan_1.position_size_pct == 1
    plan_100 = TradingPlanDetail(**_make_plan(position_size_pct=100))
    assert plan_100.position_size_pct == 100


# ---- DirectionAnalysis tests ----

def _make_analysis(**overrides):
    """Helper: build a valid DirectionAnalysis dict."""
    from app.schemas.analysis import Direction

    defaults = dict(
        direction=Direction.LONG,
        confidence=7,
        trading_plan=_make_plan(),
        reasoning="Xu hướng tăng rõ ràng.",
    )
    defaults.update(overrides)
    return defaults


def test_direction_analysis_confidence_bounds():
    """confidence must be 1-10 inclusive."""
    from app.schemas.analysis import DirectionAnalysis

    with pytest.raises(ValidationError):
        DirectionAnalysis(**_make_analysis(confidence=0))

    with pytest.raises(ValidationError):
        DirectionAnalysis(**_make_analysis(confidence=11))

    # Boundary values valid
    a1 = DirectionAnalysis(**_make_analysis(confidence=1))
    assert a1.confidence == 1
    a10 = DirectionAnalysis(**_make_analysis(confidence=10))
    assert a10.confidence == 10


def test_reasoning_field_present():
    """DirectionAnalysis.reasoning is a string field (per PLAN-06)."""
    from app.schemas.analysis import DirectionAnalysis

    analysis = DirectionAnalysis(**_make_analysis(reasoning="Test reasoning text"))
    assert isinstance(analysis.reasoning, str)
    assert analysis.reasoning == "Test reasoning text"


# ---- TickerTradingSignal tests ----

def test_ticker_trading_signal_structure():
    """Full TickerTradingSignal with both directions, recommended_direction is Direction."""
    from app.schemas.analysis import Direction, TickerTradingSignal, DirectionAnalysis

    long_data = _make_analysis(direction=Direction.LONG, confidence=8)
    bearish_data = _make_analysis(direction=Direction.BEARISH, confidence=4)

    signal = TickerTradingSignal(
        ticker="VNM",
        recommended_direction=Direction.LONG,
        long_analysis=long_data,
        bearish_analysis=bearish_data,
    )
    assert signal.ticker == "VNM"
    assert isinstance(signal.recommended_direction, Direction)
    assert signal.recommended_direction == Direction.LONG
    assert signal.long_analysis.confidence == 8
    assert signal.bearish_analysis.confidence == 4


# ---- Full batch response test ----

def test_full_batch_response():
    """TradingSignalBatchResponse with 2 tickers, round-trip via model_dump/model_validate."""
    from app.schemas.analysis import (
        Direction,
        TradingSignalBatchResponse,
        TickerTradingSignal,
    )

    signals_data = []
    for ticker in ["VNM", "FPT"]:
        long_data = _make_analysis(direction=Direction.LONG, confidence=8)
        bearish_data = _make_analysis(direction=Direction.BEARISH, confidence=3)
        signals_data.append(
            TickerTradingSignal(
                ticker=ticker,
                recommended_direction=Direction.LONG,
                long_analysis=long_data,
                bearish_analysis=bearish_data,
            )
        )

    batch = TradingSignalBatchResponse(signals=signals_data)
    assert len(batch.signals) == 2

    # Round-trip
    dumped = batch.model_dump()
    restored = TradingSignalBatchResponse.model_validate(dumped)
    assert len(restored.signals) == 2
    assert restored.signals[0].ticker == "VNM"
    assert restored.signals[1].ticker == "FPT"


# ---- AnalysisType enum test ----

def test_analysis_type_trading_signal():
    """AnalysisType includes TRADING_SIGNAL with value 'trading_signal'."""
    from app.models.ai_analysis import AnalysisType

    assert AnalysisType.TRADING_SIGNAL.value == "trading_signal"


# ---- Config settings tests ----

def test_config_trading_signal_settings():
    """Config has correct default values for 3 trading signal settings."""
    from app.config import Settings

    # Check field defaults from class metadata (avoid loading .env)
    fields = Settings.model_fields
    assert fields["trading_signal_batch_size"].default == 15
    assert fields["trading_signal_thinking_budget"].default == 2048
    assert fields["trading_signal_max_tokens"].default == 32768
