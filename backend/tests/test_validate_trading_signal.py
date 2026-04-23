"""Unit tests for _validate_trading_signal (Phase 38+39: AIQ-02)."""
import pytest
from app.schemas.analysis import (
    TickerTradingSignal,
    DirectionAnalysis,
    TradingPlanDetail,
    Direction,
    Timeframe,
)
from app.services.analysis.prompts import _validate_trading_signal


def _make_signal(
    entry: float = 80_000,
    sl: float = 78_000,
    tp1: float = 82_000,
    tp2: float = 84_000,
) -> TickerTradingSignal:
    """Helper to build a TickerTradingSignal with sensible defaults."""
    plan = TradingPlanDetail(
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=tp2,
        risk_reward_ratio=1.0,
        position_size_pct=5,
        timeframe=Timeframe.SWING,
    )
    long_analysis = DirectionAnalysis(
        direction=Direction.LONG,
        confidence=7,
        trading_plan=plan,
        reasoning="Test long analysis.",
    )
    bearish_plan = TradingPlanDetail(
        entry_price=entry,
        stop_loss=entry + 2_000,
        take_profit_1=entry - 2_000,
        take_profit_2=entry - 4_000,
        risk_reward_ratio=1.0,
        position_size_pct=3,
        timeframe=Timeframe.SWING,
    )
    bearish_analysis = DirectionAnalysis(
        direction=Direction.BEARISH,
        confidence=4,
        trading_plan=bearish_plan,
        reasoning="Test bearish analysis.",
    )
    return TickerTradingSignal(
        ticker="VNM",
        recommended_direction=Direction.LONG,
        long_analysis=long_analysis,
        bearish_analysis=bearish_analysis,
    )


class TestValidateSignalBasic:
    def test_valid_signal_passes(self):
        sig = _make_signal()
        valid, reason = _validate_trading_signal(sig, current_price=80_000, atr=1_000)
        assert valid is True
        assert reason == ""

    def test_entry_outside_5pct_of_current_price(self):
        sig = _make_signal(entry=90_000)
        valid, reason = _validate_trading_signal(sig, current_price=80_000, atr=5_000)
        assert valid is False
        assert "±5%" in reason

    def test_sl_exceeds_3x_atr(self):
        sig = _make_signal(entry=80_000, sl=70_000)
        valid, reason = _validate_trading_signal(sig, current_price=80_000, atr=1_000)
        assert valid is False
        assert "3×ATR" in reason

    def test_tp_exceeds_5x_atr(self):
        sig = _make_signal(entry=80_000, tp2=100_000)
        valid, reason = _validate_trading_signal(sig, current_price=80_000, atr=1_000)
        assert valid is False
        assert "5×ATR" in reason


class TestValidate52WeekBounds:
    def test_entry_above_52week_high(self):
        sig = _make_signal(entry=95_000)
        valid, reason = _validate_trading_signal(
            sig, current_price=95_000, atr=5_000,
            week_52_high=90_000, week_52_low=60_000,
        )
        assert valid is False
        assert "52-week" in reason

    def test_entry_below_52week_low(self):
        sig = _make_signal(entry=55_000)
        valid, reason = _validate_trading_signal(
            sig, current_price=55_000, atr=5_000,
            week_52_high=90_000, week_52_low=60_000,
        )
        assert valid is False
        assert "52-week" in reason

    def test_52week_none_skips_check(self):
        sig = _make_signal()
        valid, reason = _validate_trading_signal(
            sig, current_price=80_000, atr=1_000,
            week_52_high=None, week_52_low=None,
        )
        assert valid is True

    def test_bearish_analysis_also_checked(self):
        """Both long and bearish plans are validated — bearish can fail too."""
        plan = TradingPlanDetail(
            entry_price=80_000,
            stop_loss=78_000,
            take_profit_1=82_000,
            take_profit_2=84_000,
            risk_reward_ratio=1.0,
            position_size_pct=5,
            timeframe=Timeframe.SWING,
        )
        long_a = DirectionAnalysis(
            direction=Direction.LONG, confidence=7,
            trading_plan=plan, reasoning="ok",
        )
        # Bearish with SL way too far
        bearish_plan = TradingPlanDetail(
            entry_price=80_000,
            stop_loss=100_000,  # 20k away, far > 3×ATR
            take_profit_1=78_000,
            take_profit_2=76_000,
            risk_reward_ratio=1.0,
            position_size_pct=3,
            timeframe=Timeframe.SWING,
        )
        bearish_a = DirectionAnalysis(
            direction=Direction.BEARISH, confidence=4,
            trading_plan=bearish_plan, reasoning="test",
        )
        sig = TickerTradingSignal(
            ticker="VNM",
            recommended_direction=Direction.LONG,
            long_analysis=long_a,
            bearish_analysis=bearish_a,
        )
        valid, reason = _validate_trading_signal(sig, current_price=80_000, atr=1_000)
        assert valid is False
