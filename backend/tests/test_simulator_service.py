"""Unit tests for simulator service pure functions.

Tests calculate_buy_fee, calculate_sell_fees, and fifo_match — no DB needed.
"""
import pytest
from datetime import date
from decimal import Decimal

from app.services.simulator_service import (
    calculate_buy_fee,
    calculate_sell_fees,
    fifo_match,
    BROKER_FEE_PCT,
    SELL_TAX_PCT,
)


class TestCalculateBuyFee:
    """Tests for calculate_buy_fee: price × quantity × 0.15%."""

    def test_standard_calculation(self):
        # 100,000 × 100 = 10,000,000 → 0.15% = 15,000
        result = calculate_buy_fee(Decimal("100000"), 100)
        assert result == Decimal("15000.00")

    def test_odd_numbers_rounding(self):
        # 23,500 × 300 = 7,050,000 → 0.15% = 10,575
        result = calculate_buy_fee(Decimal("23500"), 300)
        assert result == Decimal("10575.00")

    def test_small_trade(self):
        # 10,000 × 10 = 100,000 → 0.15% = 150
        result = calculate_buy_fee(Decimal("10000"), 10)
        assert result == Decimal("150.00")

    def test_rounding_to_two_decimal_places(self):
        # 33,333 × 1 = 33,333 → 0.15% = 49.9995 → rounds to 50.00
        result = calculate_buy_fee(Decimal("33333"), 1)
        assert result == result.quantize(Decimal("0.01"))

    def test_large_trade(self):
        # 150,000 × 500 = 75,000,000 → 0.15% = 112,500
        result = calculate_buy_fee(Decimal("150000"), 500)
        assert result == Decimal("112500.00")


class TestCalculateSellFees:
    """Tests for calculate_sell_fees: returns (broker_fee, sell_tax) tuple."""

    def test_returns_tuple(self):
        result = calculate_sell_fees(Decimal("100000"), 100)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_standard_calculation(self):
        # 100,000 × 100 = 10,000,000
        # broker = 0.15% = 15,000 ; tax = 0.1% = 10,000
        broker, tax = calculate_sell_fees(Decimal("100000"), 100)
        assert broker == Decimal("15000.00")
        assert tax == Decimal("10000.00")

    def test_broker_and_tax_rates_independent(self):
        broker, tax = calculate_sell_fees(Decimal("50000"), 200)
        # 50,000 × 200 = 10,000,000
        assert broker == Decimal("15000.00")  # 0.15%
        assert tax == Decimal("10000.00")      # 0.1%
        assert broker != tax  # different rates

    def test_small_values_rounding(self):
        broker, tax = calculate_sell_fees(Decimal("10000"), 10)
        # 10,000 × 10 = 100,000
        assert broker == Decimal("150.00")  # 0.15%
        assert tax == Decimal("100.00")      # 0.1%


class TestFifoMatch:
    """Tests for fifo_match: FIFO lot matching for sell orders."""

    def _make_lot(self, id, qty, price, buy_date):
        return {
            "id": id,
            "remaining_quantity": qty,
            "buy_price": Decimal(str(price)),
            "buy_date": buy_date,
        }

    def test_single_lot_exact_match(self):
        lots = [self._make_lot(1, 100, 50000, date(2024, 1, 1))]
        matches, total_cost = fifo_match(lots, 100)
        assert len(matches) == 1
        assert matches[0]["lot_id"] == 1
        assert matches[0]["quantity"] == 100
        assert matches[0]["buy_price"] == Decimal("50000")
        assert total_cost == Decimal("5000000")

    def test_multiple_lots_fifo_order(self):
        lots = [
            self._make_lot(2, 200, 52000, date(2024, 1, 5)),
            self._make_lot(1, 100, 50000, date(2024, 1, 1)),  # oldest first
        ]
        matches, total_cost = fifo_match(lots, 150)
        # Should take 100 from lot 1 (Jan 1) first, then 50 from lot 2 (Jan 5)
        assert len(matches) == 2
        assert matches[0]["lot_id"] == 1
        assert matches[0]["quantity"] == 100
        assert matches[1]["lot_id"] == 2
        assert matches[1]["quantity"] == 50

    def test_partial_match_from_first_lot(self):
        lots = [self._make_lot(1, 200, 50000, date(2024, 1, 1))]
        matches, total_cost = fifo_match(lots, 100)
        assert len(matches) == 1
        assert matches[0]["quantity"] == 100
        assert total_cost == Decimal("5000000")

    def test_insufficient_quantity_raises(self):
        lots = [self._make_lot(1, 50, 50000, date(2024, 1, 1))]
        with pytest.raises(ValueError, match="Insufficient lots"):
            fifo_match(lots, 100)

    def test_total_cost_calculation(self):
        lots = [
            self._make_lot(1, 100, 50000, date(2024, 1, 1)),
            self._make_lot(2, 100, 60000, date(2024, 1, 5)),
        ]
        matches, total_cost = fifo_match(lots, 200)
        # 100 × 50,000 + 100 × 60,000 = 11,000,000
        assert total_cost == Decimal("11000000")

    def test_empty_lots_raises(self):
        with pytest.raises(ValueError, match="Insufficient lots"):
            fifo_match([], 100)
