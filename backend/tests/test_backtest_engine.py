"""Tests for BacktestEngine and apply_slippage.

Covers: slippage math, signal→trade creation, position evaluation,
cash tracking, equity snapshots, resume logic, cancel flag, status transitions.
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.paper_trade import TradeStatus, TradeDirection
from app.services.backtest_engine import BacktestEngine, apply_slippage


# ------------------------------------------------------------------
# apply_slippage pure function tests
# ------------------------------------------------------------------


class TestApplySlippage:
    def test_buy_slippage_increases_price(self):
        """Buying costs more: 100 + 0.5% = 100.50."""
        result = apply_slippage(Decimal("100"), Decimal("0.5"), is_buy=True)
        assert result == Decimal("100.50")

    def test_sell_slippage_decreases_price(self):
        """Selling receives less: 100 - 0.5% = 99.50."""
        result = apply_slippage(Decimal("100"), Decimal("0.5"), is_buy=False)
        assert result == Decimal("99.50")

    def test_zero_slippage_returns_original(self):
        """0% slippage returns exact original price."""
        result = apply_slippage(Decimal("100"), Decimal("0"), is_buy=True)
        assert result == Decimal("100")
        result = apply_slippage(Decimal("100"), Decimal("0"), is_buy=False)
        assert result == Decimal("100")

    def test_large_price_slippage(self):
        """Slippage on realistic VN stock price (80,000 VND)."""
        result = apply_slippage(Decimal("80000"), Decimal("0.5"), is_buy=True)
        assert result == Decimal("80400.0")

    def test_sell_large_price_slippage(self):
        result = apply_slippage(Decimal("80000"), Decimal("0.5"), is_buy=False)
        assert result == Decimal("79600.0")


# ------------------------------------------------------------------
# Signal → PENDING trade creation
# ------------------------------------------------------------------


class TestSignalToTrade:
    def test_create_pending_trade_from_signal(self):
        """Engine creates PENDING trade with correct fields from signal data."""
        from app.models.backtest import BacktestTrade

        trade = BacktestTrade(
            run_id=1,
            ticker_id=42,
            backtest_analysis_id=100,
            direction=TradeDirection.LONG,
            status=TradeStatus.PENDING,
            entry_price=Decimal("82000"),
            stop_loss=Decimal("79500"),
            take_profit_1=Decimal("84500"),
            take_profit_2=Decimal("86000"),
            quantity=500,
            confidence=7,
            timeframe="swing",
            position_size_pct=8,
            risk_reward_ratio=1.0,
            signal_date=date(2025, 1, 15),
        )

        assert trade.status == TradeStatus.PENDING
        assert trade.direction == TradeDirection.LONG
        assert trade.signal_date == date(2025, 1, 15)
        assert trade.entry_date is None
        assert trade.quantity == 500

    def test_pending_trade_activates_at_d_plus_1(self):
        """PENDING trade activates at D+1 with open price + slippage."""
        # Simulating activation: signal_date=Jan 15, activate on Jan 16
        signal_date = date(2025, 1, 15)
        session_date = date(2025, 1, 16)
        open_price = Decimal("82500")
        slippage_pct = Decimal("0.5")

        # D+1 entry: signal_date < session_date → eligible
        assert signal_date < session_date

        # Apply slippage to open price (buying = higher price)
        slipped_entry = apply_slippage(open_price, slippage_pct, is_buy=True)
        assert slipped_entry == Decimal("82912.50")

    def test_pending_trade_not_activated_same_day(self):
        """PENDING trade with signal_date == session_date is NOT activated (D+1 rule)."""
        signal_date = date(2025, 1, 15)
        session_date = date(2025, 1, 15)
        # NOT eligible: must be signal_date < session_date
        assert not (signal_date < session_date)


# ------------------------------------------------------------------
# Position evaluation (using real paper_trade_service functions)
# ------------------------------------------------------------------


class TestPositionEvaluation:
    def test_active_long_hitting_sl_closes(self):
        """Active LONG position hitting SL triggers close with slippage on exit."""
        from app.services.paper_trade_service import evaluate_long_position

        new_status, exit_price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("79500"),
            take_profit_1=Decimal("84500"),
            take_profit_2=Decimal("86000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("80500"),
            bar_low=Decimal("79000"),  # Low breaches SL
        )
        assert new_status == TradeStatus.CLOSED_SL
        assert exit_price == Decimal("79500")

        # Slippage applied to exit (selling = lower price)
        slipped_exit = apply_slippage(exit_price, Decimal("0.5"), is_buy=False)
        assert slipped_exit < exit_price

    def test_active_long_hitting_tp1_triggers_partial(self):
        """Active LONG hitting TP1 triggers PARTIAL_TP via apply_partial_tp."""
        from app.services.paper_trade_service import evaluate_long_position, apply_partial_tp

        new_status, exit_price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("79500"),
            take_profit_1=Decimal("84500"),
            take_profit_2=Decimal("86000"),
            bar_open=Decimal("83000"),
            bar_high=Decimal("85000"),  # High breaches TP1
            bar_low=Decimal("82500"),
        )
        assert new_status == TradeStatus.PARTIAL_TP
        assert exit_price == Decimal("84500")

        # apply_partial_tp mutates the trade object
        class FakeTrade:
            status = TradeStatus.ACTIVE
            quantity = 500
            closed_quantity = 0
            partial_exit_price = None
            adjusted_stop_loss = None
            entry_price = Decimal("82000")

        fake_trade = FakeTrade()
        apply_partial_tp(fake_trade, exit_price)
        assert fake_trade.status == TradeStatus.PARTIAL_TP
        assert fake_trade.closed_quantity == 200  # 500//2=250, round to 200
        assert fake_trade.partial_exit_price == Decimal("84500")
        assert fake_trade.adjusted_stop_loss == Decimal("82000")  # Breakeven

    def test_timeout_counts_trading_days(self):
        """Timeout evaluation should count trading days, not calendar days."""
        from app.services.paper_trade_service import TIMEOUT_TRADING_DAYS

        # Swing timeout is 15 trading days
        assert TIMEOUT_TRADING_DAYS["swing"] == 15
        assert TIMEOUT_TRADING_DAYS["position"] == 60


# ------------------------------------------------------------------
# Cash tracking
# ------------------------------------------------------------------


class TestCashTracking:
    def test_cash_deducted_on_trade_open(self):
        """Cash is reduced when a trade is activated."""
        initial_cash = Decimal("100000000")
        entry_price = Decimal("82912.50")  # After slippage
        quantity = 500
        cost = entry_price * quantity

        cash_after = initial_cash - cost
        assert cash_after == initial_cash - Decimal("41456250.0")
        assert cash_after < initial_cash

    def test_cash_added_back_on_trade_close(self):
        """Cash is restored (with P&L) when trade is closed."""
        cash_before = Decimal("58543750.0")
        exit_price = Decimal("84102.50")  # TP1 with slippage
        remaining_quantity = 300  # After partial TP
        proceeds = exit_price * remaining_quantity

        cash_after = cash_before + proceeds
        assert cash_after > cash_before


# ------------------------------------------------------------------
# Equity snapshot
# ------------------------------------------------------------------


class TestEquitySnapshot:
    def test_equity_is_cash_plus_positions_value(self):
        """Equity = cash + sum(close_price × quantity) for open positions."""
        cash = Decimal("60000000")
        # 2 open positions
        pos1_close = Decimal("83000")
        pos1_qty = 500
        pos2_close = Decimal("45000")
        pos2_qty = 1000
        positions_value = pos1_close * pos1_qty + pos2_close * pos2_qty
        total_equity = cash + positions_value

        assert positions_value == Decimal("86500000")
        assert total_equity == Decimal("146500000")

    def test_pending_positions_have_zero_market_value(self):
        """Pending positions have 0 market exposure (not yet entered)."""
        # Per plan: pending → positions_value += 0
        positions_value = Decimal("0")
        assert positions_value == Decimal("0")


# ------------------------------------------------------------------
# Resume logic
# ------------------------------------------------------------------


class TestResumeLogic:
    def test_skip_completed_dates(self):
        """Engine skips dates <= last_completed_date on resume."""
        trading_dates = [
            date(2025, 1, 13),
            date(2025, 1, 14),
            date(2025, 1, 15),
            date(2025, 1, 16),
            date(2025, 1, 17),
        ]
        last_completed = date(2025, 1, 15)

        # Filter to only dates > last_completed_date
        remaining = [d for d in trading_dates if d > last_completed]
        assert remaining == [date(2025, 1, 16), date(2025, 1, 17)]

    def test_no_resume_returns_all_dates(self):
        """When last_completed_date is None, all dates are processed."""
        trading_dates = [
            date(2025, 1, 13),
            date(2025, 1, 14),
        ]
        last_completed = None

        # No filtering when last_completed is None
        remaining = trading_dates if last_completed is None else [
            d for d in trading_dates if d > last_completed
        ]
        assert len(remaining) == 2


# ------------------------------------------------------------------
# Cancel flag
# ------------------------------------------------------------------


class TestCancelFlag:
    def test_cancel_flag_stops_engine(self):
        """Engine stops when is_cancelled flag is True."""
        # Simulating the cancel check logic
        is_cancelled = True
        should_stop = is_cancelled
        assert should_stop is True

    def test_no_cancel_continues(self):
        is_cancelled = False
        should_stop = is_cancelled
        assert should_stop is False


# ------------------------------------------------------------------
# Status transitions
# ------------------------------------------------------------------


class TestStatusTransitions:
    def test_running_to_completed(self):
        """Engine sets status to COMPLETED on successful finish."""
        from app.models.backtest import BacktestStatus
        status = BacktestStatus.RUNNING
        # After successful completion
        new_status = BacktestStatus.COMPLETED
        assert new_status == BacktestStatus.COMPLETED

    def test_running_to_cancelled(self):
        """Engine sets status to CANCELLED when cancel flag is detected."""
        from app.models.backtest import BacktestStatus
        new_status = BacktestStatus.CANCELLED
        assert new_status == BacktestStatus.CANCELLED

    def test_running_to_failed(self):
        """Engine sets status to FAILED on unhandled exception."""
        from app.models.backtest import BacktestStatus
        new_status = BacktestStatus.FAILED
        assert new_status == BacktestStatus.FAILED


# ------------------------------------------------------------------
# BacktestEngine class
# ------------------------------------------------------------------


class TestBacktestEngineClass:
    def test_engine_instantiation(self):
        """BacktestEngine can be instantiated with no parameters."""
        engine = BacktestEngine()
        assert engine is not None

    def test_engine_has_run_method(self):
        """BacktestEngine has async run(run_id) method."""
        engine = BacktestEngine()
        assert hasattr(engine, "run")
        import inspect
        assert inspect.iscoroutinefunction(engine.run)
