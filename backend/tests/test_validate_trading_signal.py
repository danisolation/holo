"""Unit tests for _validate_trading_signal (Phase 38+39: AIQ-02, updated Phase 80)."""
import pytest
from app.schemas.analysis import (
    TickerTradingSignal,
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
    return TickerTradingSignal(
        ticker="VNM",
        recommended_direction=Direction.LONG,
        confidence=7,
        trading_plan=plan,
        reasoning="Test long analysis.",
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
