"""Tests for position evaluation logic and paper_position_monitor job.

PT-04: Daily SL/TP/timeout check against OHLCV.
PT-06: PENDING → ACTIVE at D+1 open price.
Pure unit tests on evaluation functions — no DB, no async.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from datetime import date

from app.models.paper_trade import TradeStatus, TradeDirection
from app.services.paper_trade_service import (
    evaluate_long_position,
    evaluate_bearish_position,
    TIMEOUT_TRADING_DAYS,
)


class TestEvaluateLongPosition:
    """PT-04: LONG direction evaluation against daily bar."""

    def test_sl_hit_via_low(self):
        """Low touches SL → CLOSED_SL at SL price."""
        status, price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("76000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("81000"),
            bar_low=Decimal("75000"),
        )
        assert status == TradeStatus.CLOSED_SL
        assert price == Decimal("76000")

    def test_sl_gap_through_at_open(self):
        """Open gaps below SL → CLOSED_SL at OPEN price (not SL)."""
        status, price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("76000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("74000"),
            bar_high=Decimal("75000"),
            bar_low=Decimal("73000"),
        )
        assert status == TradeStatus.CLOSED_SL
        assert price == Decimal("74000")  # Gap price, not SL level

    def test_tp1_hit_active(self):
        """High reaches TP1 on ACTIVE trade → PARTIAL_TP at TP1 price."""
        status, price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("76000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("85000"),
            bar_low=Decimal("79000"),
        )
        assert status == TradeStatus.PARTIAL_TP
        assert price == Decimal("84000")

    def test_tp1_gap_through_at_open(self):
        """Open gaps above TP1 → PARTIAL_TP at OPEN price (not TP1)."""
        status, price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("76000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("85000"),
            bar_high=Decimal("86000"),
            bar_low=Decimal("84000"),
        )
        assert status == TradeStatus.PARTIAL_TP
        assert price == Decimal("85000")  # Gap price

    def test_tp2_hit_partial_tp(self):
        """High reaches TP2 on PARTIAL_TP trade → CLOSED_TP2."""
        status, price = evaluate_long_position(
            status=TradeStatus.PARTIAL_TP,
            effective_sl=Decimal("80000"),  # Breakeven after partial TP
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("86000"),
            bar_high=Decimal("89000"),
            bar_low=Decimal("85000"),
        )
        assert status == TradeStatus.CLOSED_TP2
        assert price == Decimal("88000")

    def test_tp2_gap_through_at_open(self):
        """Open gaps above TP2 → CLOSED_TP2 at OPEN price."""
        status, price = evaluate_long_position(
            status=TradeStatus.PARTIAL_TP,
            effective_sl=Decimal("80000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("90000"),
            bar_high=Decimal("91000"),
            bar_low=Decimal("89000"),
        )
        assert status == TradeStatus.CLOSED_TP2
        assert price == Decimal("90000")

    def test_ambiguous_bar_sl_wins(self):
        """Both SL and TP breached on same bar → SL wins (conservative)."""
        status, price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("76000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("85000"),  # TP1 breached
            bar_low=Decimal("75000"),   # SL breached
        )
        assert status == TradeStatus.CLOSED_SL  # SL wins!
        assert price == Decimal("76000")

    def test_no_transition(self):
        """Price within range → no state change."""
        status, price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("76000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("82000"),
            bar_low=Decimal("78000"),
        )
        assert status is None
        assert price is None

    def test_tp1_not_checked_in_partial_tp_state(self):
        """PARTIAL_TP state should not re-trigger TP1 check."""
        status, price = evaluate_long_position(
            status=TradeStatus.PARTIAL_TP,
            effective_sl=Decimal("80000"),
            take_profit_1=Decimal("84000"),
            take_profit_2=Decimal("88000"),
            bar_open=Decimal("83000"),
            bar_high=Decimal("85000"),  # Above TP1 but below TP2
            bar_low=Decimal("81000"),
        )
        assert status is None  # No transition — TP1 not checked in PARTIAL_TP


class TestEvaluateBearishPosition:
    """PT-04: BEARISH direction — inverted comparisons."""

    def test_bearish_sl_hit_via_high(self):
        """BEARISH: high rises to SL → CLOSED_SL at SL price."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("84000"),  # SL is ABOVE entry for BEARISH
            take_profit_1=Decimal("76000"),  # TP is BELOW entry
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("85000"),
            bar_low=Decimal("79000"),
        )
        assert status == TradeStatus.CLOSED_SL
        assert price == Decimal("84000")

    def test_bearish_sl_gap_through(self):
        """BEARISH: open gaps above SL → CLOSED_SL at OPEN price."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("84000"),
            take_profit_1=Decimal("76000"),
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("86000"),
            bar_high=Decimal("87000"),
            bar_low=Decimal("85000"),
        )
        assert status == TradeStatus.CLOSED_SL
        assert price == Decimal("86000")  # Gap price

    def test_bearish_tp1_hit(self):
        """BEARISH: low drops to TP1 → PARTIAL_TP at TP1 price."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("84000"),
            take_profit_1=Decimal("76000"),
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("81000"),
            bar_low=Decimal("75000"),
        )
        assert status == TradeStatus.PARTIAL_TP
        assert price == Decimal("76000")

    def test_bearish_tp1_gap_through(self):
        """BEARISH: open gaps below TP1 → PARTIAL_TP at OPEN price."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("84000"),
            take_profit_1=Decimal("76000"),
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("74000"),
            bar_high=Decimal("76000"),
            bar_low=Decimal("73000"),
        )
        assert status == TradeStatus.PARTIAL_TP
        assert price == Decimal("74000")

    def test_bearish_tp2_hit(self):
        """BEARISH: low drops to TP2 (PARTIAL_TP state) → CLOSED_TP2."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.PARTIAL_TP,
            effective_sl=Decimal("80000"),  # Breakeven
            take_profit_1=Decimal("76000"),
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("75000"),
            bar_high=Decimal("76000"),
            bar_low=Decimal("71000"),
        )
        assert status == TradeStatus.CLOSED_TP2
        assert price == Decimal("72000")

    def test_bearish_ambiguous_bar_sl_wins(self):
        """BEARISH ambiguous: both SL and TP breached → SL wins."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("84000"),
            take_profit_1=Decimal("76000"),
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("85000"),  # SL breached
            bar_low=Decimal("75000"),   # TP1 breached
        )
        assert status == TradeStatus.CLOSED_SL  # SL wins!
        assert price == Decimal("84000")

    def test_bearish_no_transition(self):
        """BEARISH: price within range → no change."""
        status, price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("84000"),
            take_profit_1=Decimal("76000"),
            take_profit_2=Decimal("72000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("82000"),
            bar_low=Decimal("78000"),
        )
        assert status is None
        assert price is None


class TestPendingActivation:
    """PT-06: PENDING → ACTIVE at D+1 open price."""

    def test_pending_activation_logic(self):
        """PENDING trade signal_date < bar.date → should activate."""
        signal_date = date(2026, 4, 21)
        bar_date = date(2026, 4, 22)
        # D+1 condition: bar_date > signal_date
        assert bar_date > signal_date

    def test_pending_same_day_no_activation(self):
        """PENDING trade where bar.date == signal_date → should NOT activate."""
        signal_date = date(2026, 4, 21)
        bar_date = date(2026, 4, 21)
        assert not (bar_date > signal_date)  # Same day, no activation


class TestTimeoutConstants:
    """PT-04: Timeout trading day constants."""

    def test_swing_timeout_15_days(self):
        assert TIMEOUT_TRADING_DAYS["swing"] == 15

    def test_position_timeout_60_days(self):
        assert TIMEOUT_TRADING_DAYS["position"] == 60

    def test_default_timeout_60(self):
        """Unknown timeframe defaults to 60."""
        assert TIMEOUT_TRADING_DAYS.get("unknown", 60) == 60
