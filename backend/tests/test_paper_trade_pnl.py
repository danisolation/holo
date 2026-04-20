"""Tests for P&L calculation and partial TP logic.

Pure unit tests — no DB, no async. PT-03, PT-07 coverage.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from app.models.paper_trade import TradeStatus, TradeDirection
from app.services.paper_trade_service import calculate_pnl, apply_partial_tp


class TestCalculatePnlLong:
    """PT-07: P&L calculation for LONG direction."""

    def test_long_full_exit(self):
        """LONG: entry=80000, exit=85000, qty=200 → +1,000,000 VND, +6.25%"""
        pnl, pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("85000"),
        )
        assert pnl == Decimal("1000000")
        assert pct == 6.25

    def test_long_partial_tp_then_tp2(self):
        """LONG: entry=80K, TP1=84K (100 shares), TP2=88K (100 shares) → +1,200,000"""
        pnl, pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=Decimal("84000"),
            closed_quantity=100,
            exit_price=Decimal("88000"),
        )
        assert pnl == Decimal("1200000")
        assert pct == 7.5

    def test_long_partial_tp_then_sl_breakeven(self):
        """LONG: entry=80K, TP1=84K (100), SL at breakeven=80K (100) → +400,000"""
        pnl, pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=Decimal("84000"),
            closed_quantity=100,
            exit_price=Decimal("80000"),
        )
        assert pnl == Decimal("400000")
        assert pct == 2.5

    def test_long_full_exit_loss(self):
        """LONG: entry=80000, exit=76000, qty=200 → -800,000 VND"""
        pnl, pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("76000"),
        )
        assert pnl == Decimal("-800000")
        assert pct == -5.0


class TestCalculatePnlBearish:
    """PT-07: BEARISH direction — inverted P&L (profit when price drops)."""

    def test_bearish_full_exit_profit(self):
        """BEARISH: entry=80000, exit=75000, qty=200 → +1,000,000"""
        pnl, pct = calculate_pnl(
            direction="bearish",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("75000"),
        )
        assert pnl == Decimal("1000000")
        assert pct == 6.25

    def test_bearish_full_exit_loss(self):
        """BEARISH: entry=80000, exit=85000, qty=200 → -1,000,000"""
        pnl, pct = calculate_pnl(
            direction="bearish",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("85000"),
        )
        assert pnl == Decimal("-1000000")
        assert pct == -6.25

    def test_bearish_partial_tp(self):
        """BEARISH: entry=80K, TP1=76K (100), TP2=72K (100) → +1,200,000"""
        pnl, pct = calculate_pnl(
            direction="bearish",
            entry_price=Decimal("80000"),
            quantity=200,
            partial_exit_price=Decimal("76000"),
            closed_quantity=100,
            exit_price=Decimal("72000"),
        )
        assert pnl == Decimal("1200000")
        assert pct == 7.5


class TestPnlReturnTypes:
    """PT-07: P&L returns both VND (Decimal) and percentage (float)."""

    def test_pnl_returns_vnd_and_pct(self):
        pnl, pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("80000"),
            quantity=100,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("82000"),
        )
        assert isinstance(pnl, Decimal)
        assert isinstance(pct, float)


class TestApplyPartialTp:
    """PT-03: Partial TP — 50% close, SL moves to breakeven."""

    def _make_trade(self, status=TradeStatus.ACTIVE, quantity=200,
                    entry_price=Decimal("80000")):
        """Create a mock PaperTrade for testing."""
        trade = MagicMock()
        trade.status = status
        trade.quantity = quantity
        trade.entry_price = entry_price
        trade.closed_quantity = 0
        trade.partial_exit_price = None
        trade.adjusted_stop_loss = None
        return trade

    def test_apply_partial_tp_sets_fields(self):
        """PT-03: 50% closed, SL moved to entry (breakeven)."""
        trade = self._make_trade(quantity=200, entry_price=Decimal("80000"))
        apply_partial_tp(trade, tp1_price=Decimal("84000"))
        assert trade.status == TradeStatus.PARTIAL_TP
        assert trade.closed_quantity == 100
        assert trade.partial_exit_price == Decimal("84000")
        assert trade.adjusted_stop_loss == Decimal("80000")

    def test_apply_partial_tp_lot_rounding_300(self):
        """PT-03: 300 shares → half=150 → rounds down to 100."""
        trade = self._make_trade(quantity=300)
        apply_partial_tp(trade, tp1_price=Decimal("84000"))
        assert trade.closed_quantity == 100

    def test_apply_partial_tp_lot_rounding_400(self):
        """400 shares → half=200 → 200 (already 100-lot clean)."""
        trade = self._make_trade(quantity=400)
        apply_partial_tp(trade, tp1_price=Decimal("84000"))
        assert trade.closed_quantity == 200

    def test_apply_partial_tp_100_shares(self):
        """100 shares → half=50 → rounds to 0 → special case: close all."""
        trade = self._make_trade(quantity=100)
        apply_partial_tp(trade, tp1_price=Decimal("84000"))
        assert trade.closed_quantity == 100

    def test_apply_partial_tp_invalid_from_pending(self):
        trade = self._make_trade(status=TradeStatus.PENDING)
        with pytest.raises(ValueError, match="Cannot apply partial TP"):
            apply_partial_tp(trade, tp1_price=Decimal("84000"))

    def test_apply_partial_tp_invalid_from_closed(self):
        trade = self._make_trade(status=TradeStatus.CLOSED_SL)
        with pytest.raises(ValueError, match="Cannot apply partial TP"):
            apply_partial_tp(trade, tp1_price=Decimal("84000"))
