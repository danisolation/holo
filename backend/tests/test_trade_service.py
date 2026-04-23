"""Unit tests for trade service pure functions.

Tests FIFO lot matching, fee calculation, and realized P&L calculation.
These are pure function tests — no database or async needed.
"""
import pytest
from decimal import Decimal

from app.services.trade_service import (
    calculate_broker_fee,
    calculate_sell_tax,
    fifo_match_lots,
    calculate_realized_pnl,
)


# ── Fee Calculation Tests ────────────────────────────────────────────────────


class TestFeeCalculation:
    """Test broker fee and sell tax calculations."""

    def test_broker_fee_standard(self):
        """Standard 0.15% broker fee on 200 shares @ 60,000 VND."""
        result = calculate_broker_fee(Decimal("60000"), 200, Decimal("0.150"))
        assert result == Decimal("18000.00")

    def test_broker_fee_custom_pct(self):
        """Custom 0.20% broker fee on 100 shares @ 50,000 VND."""
        result = calculate_broker_fee(Decimal("50000"), 100, Decimal("0.200"))
        assert result == Decimal("10000.00")

    def test_broker_fee_small_trade(self):
        """Small trade: 100 shares @ 10,000 VND with 0.15%."""
        result = calculate_broker_fee(Decimal("10000"), 100, Decimal("0.150"))
        assert result == Decimal("1500.00")

    def test_broker_fee_large_trade(self):
        """Large trade: 1000 shares @ 100,000 VND with 0.15%."""
        result = calculate_broker_fee(Decimal("100000"), 1000, Decimal("0.150"))
        assert result == Decimal("150000.00")

    def test_sell_tax_standard(self):
        """Standard 0.1% sell tax on 200 shares @ 60,000 VND."""
        result = calculate_sell_tax(Decimal("60000"), 200)
        assert result == Decimal("12000.00")

    def test_sell_tax_small(self):
        """Sell tax on small trade: 100 shares @ 10,000 VND."""
        result = calculate_sell_tax(Decimal("10000"), 100)
        assert result == Decimal("1000.00")


# ── FIFO Matching Tests ──────────────────────────────────────────────────────


class TestFIFOMatching:
    """Test FIFO lot matching algorithm."""

    def test_single_lot_exact(self):
        """Exact match: sell 200, one lot with 200 remaining."""
        lots = [{"id": 1, "remaining_quantity": 200, "buy_price": Decimal("50000")}]
        matches = fifo_match_lots(lots, 200)
        assert len(matches) == 1
        assert matches[0]["lot_id"] == 1
        assert matches[0]["matched_quantity"] == 200
        assert matches[0]["buy_price"] == Decimal("50000")

    def test_multiple_lots_partial(self):
        """Partial match: sell 300 from lots of [200, 300] = consume 200 + 100."""
        lots = [
            {"id": 1, "remaining_quantity": 200, "buy_price": Decimal("50000")},
            {"id": 2, "remaining_quantity": 300, "buy_price": Decimal("55000")},
        ]
        matches = fifo_match_lots(lots, 300)
        assert len(matches) == 2
        assert matches[0] == {"lot_id": 1, "buy_price": Decimal("50000"), "matched_quantity": 200}
        assert matches[1] == {"lot_id": 2, "buy_price": Decimal("55000"), "matched_quantity": 100}

    def test_consume_all_lots(self):
        """Sell exactly the total of all lots."""
        lots = [
            {"id": 1, "remaining_quantity": 100, "buy_price": Decimal("40000")},
            {"id": 2, "remaining_quantity": 200, "buy_price": Decimal("45000")},
        ]
        matches = fifo_match_lots(lots, 300)
        assert len(matches) == 2
        assert matches[0]["matched_quantity"] == 100
        assert matches[1]["matched_quantity"] == 200

    def test_insufficient_lots_empty(self):
        """Raise ValueError when no lots available."""
        with pytest.raises(ValueError, match="Insufficient lots"):
            fifo_match_lots([], 100)

    def test_insufficient_lots_partial(self):
        """Raise ValueError when lots < sell quantity."""
        lots = [{"id": 1, "remaining_quantity": 50, "buy_price": Decimal("50000")}]
        with pytest.raises(ValueError, match="Insufficient lots"):
            fifo_match_lots(lots, 100)

    def test_fifo_order_preserved(self):
        """FIFO: oldest lot consumed first even if newer lot is larger."""
        lots = [
            {"id": 1, "remaining_quantity": 100, "buy_price": Decimal("50000")},  # oldest
            {"id": 2, "remaining_quantity": 500, "buy_price": Decimal("55000")},  # newer, larger
        ]
        matches = fifo_match_lots(lots, 200)
        assert matches[0]["lot_id"] == 1
        assert matches[0]["matched_quantity"] == 100
        assert matches[1]["lot_id"] == 2
        assert matches[1]["matched_quantity"] == 100


# ── P&L Calculation Tests ────────────────────────────────────────────────────


class TestPnLCalculation:
    """Test realized P&L calculation from lot matches."""

    def test_simple_profit(self):
        """Simple profit: buy @ 50k, sell @ 60k, 200 shares."""
        matches = [{"buy_price": Decimal("50000"), "matched_quantity": 200}]
        gross, net = calculate_realized_pnl(
            sell_price=Decimal("60000"),
            matches=matches,
            sell_broker_fee=Decimal("18000"),
            sell_tax=Decimal("12000"),
            buy_broker_fees=Decimal("15000"),
        )
        assert gross == Decimal("2000000")  # (60000-50000) × 200
        assert net == Decimal("1955000")    # 2000000 - 18000 - 12000 - 15000

    def test_loss(self):
        """Loss: buy @ 50k, sell @ 45k, 200 shares."""
        matches = [{"buy_price": Decimal("50000"), "matched_quantity": 200}]
        gross, net = calculate_realized_pnl(
            sell_price=Decimal("45000"),
            matches=matches,
            sell_broker_fee=Decimal("13500"),
            sell_tax=Decimal("9000"),
            buy_broker_fees=Decimal("15000"),
        )
        assert gross == Decimal("-1000000")  # (45000-50000) × 200
        assert net == Decimal("-1037500")    # -1000000 - 13500 - 9000 - 15000

    def test_multi_lot_pnl(self):
        """Multiple lots with different buy prices."""
        matches = [
            {"buy_price": Decimal("50000"), "matched_quantity": 200},
            {"buy_price": Decimal("55000"), "matched_quantity": 100},
        ]
        gross, net = calculate_realized_pnl(
            sell_price=Decimal("60000"),
            matches=matches,
            sell_broker_fee=Decimal("27000"),
            sell_tax=Decimal("18000"),
            buy_broker_fees=Decimal("23250"),
        )
        # gross = (60000-50000)×200 + (60000-55000)×100 = 2000000 + 500000 = 2500000
        assert gross == Decimal("2500000")
        # net = 2500000 - 27000 - 18000 - 23250 = 2431750
        assert net == Decimal("2431750")

    def test_breakeven(self):
        """Breakeven: same buy/sell price, P&L = -fees only."""
        matches = [{"buy_price": Decimal("50000"), "matched_quantity": 100}]
        gross, net = calculate_realized_pnl(
            sell_price=Decimal("50000"),
            matches=matches,
            sell_broker_fee=Decimal("7500"),
            sell_tax=Decimal("5000"),
            buy_broker_fees=Decimal("7500"),
        )
        assert gross == Decimal("0")
        assert net == Decimal("-20000")  # 0 - 7500 - 5000 - 7500
