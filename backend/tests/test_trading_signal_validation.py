"""Tests for trading signal post-validation logic.

Phase 19 Plan 02: Validates _validate_trading_signal against price/ATR bounds.
Pure unit tests — no DB, no async. Updated Phase 80 for single-direction schema.
"""
import pytest
from app.services.ai_analysis_service import _validate_trading_signal
from app.schemas.analysis import (
    Direction, Timeframe, TradingPlanDetail,
    TickerTradingSignal,
)


def _make_signal(
    entry=82000, sl=79500, tp1=84500, tp2=86000,
) -> TickerTradingSignal:
    """Helper: create a valid TickerTradingSignal for testing."""
    return TickerTradingSignal(
        ticker="VNM",
        recommended_direction=Direction.LONG,
        confidence=7,
        trading_plan=TradingPlanDetail(
            entry_price=entry, stop_loss=sl,
            take_profit_1=tp1, take_profit_2=tp2,
            risk_reward_ratio=1.0, position_size_pct=8,
            timeframe=Timeframe.SWING,
        ),
        reasoning="Test LONG reasoning",
    )


class TestValidateTradingSignal:
    def test_valid_signal(self):
        signal = _make_signal()
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=1500)
        assert is_valid is True
        assert reason == ""

    def test_entry_outside_5_percent(self):
        signal = _make_signal(entry=90000)  # 9.8% above 82000
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=1500)
        assert is_valid is False
        assert "±5%" in reason

    def test_sl_exceeds_3x_atr(self):
        signal = _make_signal(sl=75000)  # 7000 from entry, 3×ATR = 4500
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=1500)
        assert is_valid is False
        assert "3×ATR" in reason

    def test_tp_exceeds_5x_atr(self):
        signal = _make_signal(tp1=92000)  # 10000 from entry, 5×ATR = 7500
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=1500)
        assert is_valid is False
        assert "5×ATR" in reason

    def test_edge_case_exactly_5_percent(self):
        # 82000 * 1.05 = 86100 → entry at 86100 is exactly 5%
        # Also adjust sl to be within 3×ATR (3×2000=6000) of new entry
        signal = _make_signal(entry=86100, sl=82000, tp1=88000, tp2=89000)
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=2000)
        assert is_valid is True

    def test_zero_atr_skips_atr_checks(self):
        signal = _make_signal(sl=50000)  # Far SL but ATR=0 should skip check
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=0)
        assert is_valid is True  # Only entry check applies (within 5%)

    def test_invalid_signal_fields(self):
        """Verify the return tuple matches expected structure for invalid signals."""
        signal = _make_signal(entry=100000)
        is_valid, reason = _validate_trading_signal(signal, current_price=82000, atr=1500)
        assert is_valid is False
        assert isinstance(reason, str)
        assert len(reason) > 0
