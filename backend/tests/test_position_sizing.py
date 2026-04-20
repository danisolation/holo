"""Tests for position sizing with 100-share lot rounding.

Pure unit tests — no DB, no async. PT-05 coverage.
"""
import pytest
from decimal import Decimal
from app.services.paper_trade_service import calculate_position_size


class TestPositionSizing:
    """PT-05: Position sizing rounds to 100-share lots."""

    def test_rounds_to_100_lots(self):
        """100M × 10% / 50K = 200 shares → 200"""
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=10,
            entry_price=Decimal("50000"),
        )
        assert result == 200

    def test_exact_100_shares(self):
        """100M × 5% / 50K = 100 shares → 100"""
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=5,
            entry_price=Decimal("50000"),
        )
        assert result == 100

    def test_large_position(self):
        """100M × 20% / 25K = 800 shares → 800"""
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=20,
            entry_price=Decimal("25000"),
        )
        assert result == 800

    def test_rounds_down_not_up(self):
        """100M × 7% / 40K = 175 → rounds down to 100"""
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=7,
            entry_price=Decimal("40000"),
        )
        assert result == 100

    def test_minimum_100_when_affordable(self):
        """100M × 6% / 50K = 120 → rounds to 100."""
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=6,
            entry_price=Decimal("50000"),
        )
        assert result == 100

    def test_zero_when_cannot_afford_100(self):
        """100M × 1% / 120K = 8.33 → 0 lots. Can afford 100? 1M < 12M → no → 0"""
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=1,
            entry_price=Decimal("120000"),
        )
        assert result == 0

    def test_insufficient_capital(self):
        """1M × 5% / 80K = 0.625 → 0 raw → 0"""
        result = calculate_position_size(
            capital=Decimal("1000000"),
            allocation_pct=5,
            entry_price=Decimal("80000"),
        )
        assert result == 0

    def test_returns_int(self):
        result = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=10,
            entry_price=Decimal("50000"),
        )
        assert isinstance(result, int)
