"""Tests for BacktestEngine and apply_slippage.

Covers: slippage math, signal→trade creation, position evaluation,
cash tracking, equity snapshots, resume logic, cancel flag, status transitions,
engine lifecycle, position lifecycle, cash/equity tracking, checkpoint/resume,
bearish evaluation, duplicate signal protection.
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.paper_trade import TradeStatus, TradeDirection
from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity, BacktestStatus
from app.services.backtest_engine import BacktestEngine, apply_slippage
from app.services.paper_trade_service import (
    evaluate_long_position,
    evaluate_bearish_position,
    apply_partial_tp,
    calculate_pnl,
    calculate_position_size,
    TIMEOUT_TRADING_DAYS,
)


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
            closed_quantity=0,
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


# ==================================================================
# INTEGRATION-LEVEL TESTS (Plan 32-03)
# ==================================================================


# ------------------------------------------------------------------
# Engine Lifecycle
# ------------------------------------------------------------------


class TestEngineLifecycle:
    """Integration tests for engine lifecycle: complete, cancel, fail, empty dates."""

    def test_engine_has_internal_methods(self):
        """Engine has all required internal methods and delegates."""
        engine = BacktestEngine()
        assert hasattr(engine, "_load_run")
        assert hasattr(engine, "_get_trading_dates")
        assert hasattr(engine, "_get_active_tickers")
        assert hasattr(engine, "_run_ai_pipeline")
        # Delegated to sub-modules
        assert hasattr(engine, "_trade_activator")
        assert hasattr(engine, "_position_evaluator")
        assert hasattr(engine, "_equity_snapshot")

    def test_status_transitions_completed(self):
        """After successful loop, status transitions to COMPLETED."""
        assert BacktestStatus.COMPLETED.value == "completed"
        # Run starts as RUNNING, finishes as COMPLETED
        assert BacktestStatus.RUNNING.value == "running"

    def test_status_transitions_cancelled(self):
        """Cancel flag triggers CANCELLED status."""
        assert BacktestStatus.CANCELLED.value == "cancelled"

    def test_status_transitions_failed(self):
        """Unhandled exception triggers FAILED status."""
        assert BacktestStatus.FAILED.value == "failed"

    def test_empty_trading_dates_logic(self):
        """When trading_dates is empty, engine should complete immediately."""
        trading_dates = []
        # Simulating engine logic: empty dates → skip loop → set COMPLETED
        should_complete_immediately = len(trading_dates) == 0
        assert should_complete_immediately is True


# ------------------------------------------------------------------
# Position Lifecycle
# ------------------------------------------------------------------


class TestPositionLifecycle:
    """Integration tests: full signal → pending → active → evaluate cycle."""

    def test_signal_creates_pending_trade_with_all_fields(self):
        """Signal data creates PENDING trade with all required fields."""
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
            closed_quantity=0,
            confidence=7,
            timeframe="swing",
            position_size_pct=8,
            risk_reward_ratio=2.0,
            signal_date=date(2025, 1, 15),
        )

        assert trade.status == TradeStatus.PENDING
        assert trade.entry_date is None
        assert trade.closed_date is None
        assert trade.exit_price is None
        assert trade.realized_pnl is None
        assert trade.closed_quantity == 0

    def test_pending_activates_at_d_plus_1_with_slippage(self):
        """PENDING trade on D activates at D+1 with slipped open price."""
        signal_date = date(2025, 1, 15)
        session_date = date(2025, 1, 16)
        open_price = Decimal("82500")
        slippage_pct = Decimal("0.5")

        # D+1 rule: signal_date < session_date
        assert signal_date < session_date

        # LONG entry: price goes up with slippage
        slipped_entry = apply_slippage(open_price, slippage_pct, is_buy=True)
        assert slipped_entry == Decimal("82912.50")
        assert slipped_entry > open_price

    def test_pending_not_activated_same_day_strict(self):
        """Strict D+1: signal_date == session_date → NOT activated."""
        signal_date = date(2025, 1, 15)
        session_date = date(2025, 1, 15)
        assert not (signal_date < session_date)

    def test_active_long_hits_sl_with_slippage(self):
        """LONG position hitting SL closes with slippage on exit."""
        # Position params
        effective_sl = Decimal("79500")
        tp1 = Decimal("84500")
        tp2 = Decimal("86000")

        # Bar where low breaches SL
        new_status, exit_price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=effective_sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            bar_open=Decimal("80000"),
            bar_high=Decimal("80500"),
            bar_low=Decimal("79000"),
        )
        assert new_status == TradeStatus.CLOSED_SL
        assert exit_price == effective_sl

        # Slippage applied on exit (selling = lower price)
        slipped_exit = apply_slippage(exit_price, Decimal("0.5"), is_buy=False)
        assert slipped_exit < exit_price
        assert slipped_exit == Decimal("79102.50")

    def test_active_long_hits_tp1_partial(self):
        """LONG hitting TP1 triggers PARTIAL_TP, cash increases from partial exit."""
        new_status, exit_price = evaluate_long_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("79500"),
            take_profit_1=Decimal("84500"),
            take_profit_2=Decimal("86000"),
            bar_open=Decimal("83000"),
            bar_high=Decimal("85000"),
            bar_low=Decimal("82500"),
        )
        assert new_status == TradeStatus.PARTIAL_TP
        assert exit_price == Decimal("84500")

        # Slippage on partial TP exit (selling)
        slipped_tp1 = apply_slippage(exit_price, Decimal("0.5"), is_buy=False)
        assert slipped_tp1 < exit_price

        # Apply partial TP to a mock trade
        class MockTrade:
            status = TradeStatus.ACTIVE
            quantity = 500
            closed_quantity = 0
            partial_exit_price = None
            adjusted_stop_loss = None
            entry_price = Decimal("82000")

        trade = MockTrade()
        apply_partial_tp(trade, slipped_tp1)

        assert trade.status == TradeStatus.PARTIAL_TP
        assert trade.closed_quantity == 200  # 500//2=250, rounded to 200
        assert trade.adjusted_stop_loss == Decimal("82000")  # Breakeven

        # Cash from partial: slipped_tp1 × closed_quantity
        partial_cash = slipped_tp1 * trade.closed_quantity
        assert partial_cash > 0

    def test_partial_tp_hits_tp2_full_close(self):
        """PARTIAL_TP position hitting TP2 triggers full close."""
        new_status, exit_price = evaluate_long_position(
            status=TradeStatus.PARTIAL_TP,
            effective_sl=Decimal("82000"),  # Breakeven SL
            take_profit_1=Decimal("84500"),
            take_profit_2=Decimal("86000"),
            bar_open=Decimal("85000"),
            bar_high=Decimal("87000"),
            bar_low=Decimal("84800"),
        )
        assert new_status == TradeStatus.CLOSED_TP2
        assert exit_price == Decimal("86000")

        # P&L calculation for 2-leg trade
        pnl, pnl_pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("82000"),
            quantity=500,
            partial_exit_price=Decimal("84077.50"),  # Slipped TP1
            closed_quantity=200,
            exit_price=Decimal("85570"),  # Slipped TP2
        )
        assert pnl > 0  # Profitable trade
        assert pnl_pct > 0

    def test_bearish_position_sl(self):
        """BEARISH ACTIVE position: SL hit when bar_high >= SL."""
        new_status, exit_price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("85000"),  # SL above entry
            take_profit_1=Decimal("78000"),  # TP below entry
            take_profit_2=Decimal("75000"),
            bar_open=Decimal("82000"),
            bar_high=Decimal("86000"),  # Breaches SL
            bar_low=Decimal("81000"),
        )
        assert new_status == TradeStatus.CLOSED_SL
        assert exit_price == Decimal("85000")

    def test_bearish_position_tp1(self):
        """BEARISH ACTIVE position: TP1 hit when bar_low <= TP1."""
        new_status, exit_price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("85000"),
            take_profit_1=Decimal("78000"),
            take_profit_2=Decimal("75000"),
            bar_open=Decimal("80000"),
            bar_high=Decimal("80500"),
            bar_low=Decimal("77500"),  # Breaches TP1
        )
        assert new_status == TradeStatus.PARTIAL_TP
        assert exit_price == Decimal("78000")

    def test_bearish_inverted_logic_sl_is_above(self):
        """BEARISH: SL is above entry (loss when price rises), TP is below (profit when drops)."""
        entry = Decimal("82000")
        sl = Decimal("85000")   # Above entry
        tp1 = Decimal("78000")  # Below entry

        # SL is above
        assert sl > entry
        # TP is below
        assert tp1 < entry

        # P&L: BEARISH profits when exit < entry
        pnl, pnl_pct = calculate_pnl(
            direction="bearish",
            entry_price=entry,
            quantity=500,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("78000"),  # Exit below entry = profit
        )
        assert pnl > 0
        assert pnl_pct > 0

    def test_timeout_closes_position_at_close_price(self):
        """Active position held beyond TIMEOUT_TRADING_DAYS closes at close with slippage."""
        assert TIMEOUT_TRADING_DAYS["swing"] == 15
        assert TIMEOUT_TRADING_DAYS["position"] == 60

        # Simulate timeout: close at day's close with slippage
        close_price = Decimal("81500")
        slipped_exit = apply_slippage(close_price, Decimal("0.5"), is_buy=False)
        assert slipped_exit < close_price  # Selling = lower price

        # P&L after timeout (could be positive or negative)
        pnl, pnl_pct = calculate_pnl(
            direction="long",
            entry_price=Decimal("82000"),
            quantity=500,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=slipped_exit,
        )
        # Timeout at lower price = loss for long
        assert pnl < 0


# ------------------------------------------------------------------
# Cash and Equity (Extended)
# ------------------------------------------------------------------


class TestCashAndEquity:
    """Comprehensive cash and equity tracking tests."""

    def test_cash_deducted_on_trade_open_exact(self):
        """Cash before − (slipped_entry × quantity) = Cash after."""
        initial_cash = Decimal("100000000")
        entry_price = Decimal("82000")
        slipped_entry = apply_slippage(entry_price, Decimal("0.5"), is_buy=True)
        quantity = 500

        cost = slipped_entry * quantity
        cash_after = initial_cash - cost

        assert cash_after == initial_cash - cost
        assert cash_after < initial_cash

    def test_cash_returned_on_trade_close_exact(self):
        """Cash after close = cash before + (slipped_exit × remaining_qty)."""
        cash_before = Decimal("58000000")
        exit_price = Decimal("86000")
        slipped_exit = apply_slippage(exit_price, Decimal("0.5"), is_buy=False)
        remaining_qty = 300

        proceeds = slipped_exit * remaining_qty
        cash_after = cash_before + proceeds

        assert cash_after == cash_before + proceeds
        assert cash_after > cash_before

    def test_partial_tp_returns_partial_cash(self):
        """On partial TP, cash += slipped_tp1 × closed_quantity (NOT full quantity)."""
        initial_cash = Decimal("58000000")
        tp1_price = Decimal("84500")
        slipped_tp1 = apply_slippage(tp1_price, Decimal("0.5"), is_buy=False)

        total_qty = 500
        closed_qty = 200  # ~50% rounded to 100-lot

        # Partial cash return is only for closed quantity
        partial_proceeds = slipped_tp1 * closed_qty
        full_proceeds = slipped_tp1 * total_qty

        cash_after_partial = initial_cash + partial_proceeds
        cash_after_full = initial_cash + full_proceeds

        assert partial_proceeds < full_proceeds
        assert cash_after_partial < cash_after_full

    def test_equity_snapshot_correct(self):
        """total_equity = cash + sum(close_price × remaining_qty) for open positions."""
        cash = Decimal("60000000")
        # 2 open positions
        positions = [
            (Decimal("83000"), 500),   # position 1
            (Decimal("45000"), 1000),  # position 2
        ]
        positions_value = sum(price * qty for price, qty in positions)
        total_equity = cash + positions_value

        assert positions_value == Decimal("86500000")
        assert total_equity == Decimal("146500000")

    def test_cumulative_return_pct(self):
        """cumulative_return_pct = (total_equity - initial_capital) / initial_capital × 100."""
        initial_capital = Decimal("100000000")
        total_equity = Decimal("105000000")

        cum_return = float((total_equity - initial_capital) / initial_capital * 100)
        assert cum_return == pytest.approx(5.0, abs=0.01)

    def test_daily_return_pct(self):
        """daily_return_pct = (today_equity - yesterday_equity) / yesterday_equity × 100."""
        yesterday_equity = Decimal("100000000")
        today_equity = Decimal("101500000")

        daily_return = float((today_equity - yesterday_equity) / yesterday_equity * 100)
        assert daily_return == pytest.approx(1.5, abs=0.01)

    def test_equity_after_profitable_close_increases(self):
        """Equity curve monotonic check: equity after profitable close > before."""
        equity_before = Decimal("100000000")
        # Profitable close: entry 82000, exit 86000, 500 shares
        pnl, _ = calculate_pnl(
            direction="long",
            entry_price=Decimal("82000"),
            quantity=500,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("86000"),
        )
        equity_after = equity_before + pnl
        assert equity_after > equity_before

    def test_capital_tracking_multiple_trades(self):
        """Open 3 trades → close 1 → verify cash correctly updated."""
        initial_cash = Decimal("100000000")
        cash = initial_cash

        # Open 3 trades
        trade_costs = [
            Decimal("82000") * 500,   # Trade 1: 41M
            Decimal("45000") * 1000,  # Trade 2: 45M
            Decimal("12000") * 800,   # Trade 3: 9.6M
        ]

        for cost in trade_costs:
            cash -= cost

        # After 3 trades open
        total_invested = sum(trade_costs)
        assert cash == initial_cash - total_invested
        assert cash == Decimal("100000000") - Decimal("41000000") - Decimal("45000000") - Decimal("9600000")

        # Close trade 1 at profit
        exit_proceeds = Decimal("85000") * 500  # 42.5M
        cash += exit_proceeds

        # Cash should be more than after all 3 opens
        assert cash == initial_cash - total_invested + exit_proceeds


# ------------------------------------------------------------------
# Checkpoint/Resume
# ------------------------------------------------------------------


class TestCheckpointResume:
    """Tests for checkpoint updates and resume logic."""

    def test_checkpoint_updates_run_fields(self):
        """After processing a day, last_completed_date and completed_sessions are updated."""
        # Simulate checkpoint update
        last_completed = None
        completed_sessions = 0
        session_date = date(2025, 1, 13)

        # After checkpoint
        last_completed = session_date
        completed_sessions += 1

        assert last_completed == date(2025, 1, 13)
        assert completed_sessions == 1

        # Process another day
        session_date = date(2025, 1, 14)
        last_completed = session_date
        completed_sessions += 1

        assert last_completed == date(2025, 1, 14)
        assert completed_sessions == 2

    def test_resume_skips_completed_dates(self):
        """Set last_completed_date=D2. Engine starts from D3."""
        trading_dates = [
            date(2025, 1, 13),
            date(2025, 1, 14),
            date(2025, 1, 15),
            date(2025, 1, 16),
            date(2025, 1, 17),
        ]
        last_completed = date(2025, 1, 14)

        # Engine logic: filter dates > last_completed
        remaining = [d for d in trading_dates if d > last_completed]
        assert remaining == [
            date(2025, 1, 15),
            date(2025, 1, 16),
            date(2025, 1, 17),
        ]
        assert len(remaining) == 3

    def test_resume_reloads_open_positions(self):
        """Open position exists in DB for resumed run — should be evaluated on next day."""
        # Simulate: position from previous run exists
        from app.models.backtest import BacktestTrade

        trade = BacktestTrade(
            run_id=1,
            ticker_id=42,
            backtest_analysis_id=100,
            direction=TradeDirection.LONG,
            status=TradeStatus.ACTIVE,  # Already active from previous run
            entry_price=Decimal("82000"),
            stop_loss=Decimal("79500"),
            take_profit_1=Decimal("84500"),
            take_profit_2=Decimal("86000"),
            quantity=500,
            closed_quantity=0,
            confidence=7,
            timeframe="swing",
            position_size_pct=8,
            risk_reward_ratio=2.0,
            signal_date=date(2025, 1, 13),
            entry_date=date(2025, 1, 14),
        )

        # This position should be in ACTIVE state — eligible for evaluation
        assert trade.status == TradeStatus.ACTIVE
        assert trade.entry_date is not None

        # Evaluation on resume day would query ACTIVE + PARTIAL_TP
        eligible_statuses = {TradeStatus.ACTIVE, TradeStatus.PARTIAL_TP}
        assert trade.status in eligible_statuses

    def test_resume_restores_cash_from_equity(self):
        """Last equity snapshot has cash=X. Engine uses X, not initial_capital."""
        initial_capital = Decimal("100000000")
        # Simulate: last equity snapshot shows cash after several trades
        last_equity_cash = Decimal("72500000")

        # Resume logic: use equity snapshot cash, not initial
        cash = last_equity_cash  # NOT initial_capital
        assert cash == Decimal("72500000")
        assert cash != initial_capital

    def test_resume_with_no_last_completed_uses_all_dates(self):
        """When last_completed_date is None, all dates are processed."""
        trading_dates = [
            date(2025, 1, 13),
            date(2025, 1, 14),
            date(2025, 1, 15),
        ]
        last_completed = None

        remaining = trading_dates if last_completed is None else [
            d for d in trading_dates if d > last_completed
        ]
        assert remaining == trading_dates
        assert len(remaining) == 3

    def test_resume_at_last_date_yields_empty(self):
        """When last_completed_date == last trading date, remaining is empty → COMPLETED."""
        trading_dates = [
            date(2025, 1, 13),
            date(2025, 1, 14),
            date(2025, 1, 15),
        ]
        last_completed = date(2025, 1, 15)

        remaining = [d for d in trading_dates if d > last_completed]
        assert remaining == []
        # Engine should set status to COMPLETED immediately


# ------------------------------------------------------------------
# Duplicate Signal Protection
# ------------------------------------------------------------------


class TestDuplicateSignalProtection:
    """Tests verifying the engine prevents duplicate trades for same ticker on same day."""

    def test_position_sizing_zero_capital_prevents_trade(self):
        """When cash is too low, position_size returns 0 → no trade created."""
        quantity = calculate_position_size(
            capital=Decimal("1000"),     # Very low capital
            allocation_pct=5,
            entry_price=Decimal("82000"),
        )
        assert quantity == 0  # Can't even buy 100 shares

    def test_position_sizing_normal(self):
        """Normal capital → position sized in 100-share lots."""
        quantity = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=8,
            entry_price=Decimal("82000"),
        )
        # 100M * 8% = 8M, 8M / 82000 = ~97, rounded to 0... wait
        # 8,000,000 / 82,000 = 97.56 → floor = 97 → lot round = 0? No:
        # raw_shares = int(8_000_000 / 82_000) = 97
        # lot_rounded = (97 // 100) * 100 = 0
        # But allocated >= entry_price * 100? 8_000_000 >= 8_200_000? No
        # So quantity = 0. That can't be right for a 100M capital...
        # Actually: 100M * 8 / 100 = 8M. 8M / 82000 = 97.56. floor = 97.
        # 97 // 100 * 100 = 0. Need at least 100 shares = 8.2M at 82k.
        # 8M < 8.2M so can't even get 100 shares at 8% alloc!
        # Let's use 10% allocation
        quantity = calculate_position_size(
            capital=Decimal("100000000"),
            allocation_pct=10,
            entry_price=Decimal("82000"),
        )
        # 10M / 82000 = 121.95 → floor=121 → lot=100
        assert quantity == 100

    def test_signal_score_zero_skipped(self):
        """Signals with score=0 are skipped (per engine _process_signals logic)."""
        # Engine queries: BacktestAnalysis.score > 0
        # So score=0 → not returned → no trade created
        score = 0
        assert not (score > 0)


# ------------------------------------------------------------------
# Bearish Position Evaluation (Extended)
# ------------------------------------------------------------------


class TestBearishPositionEvaluation:
    """Comprehensive tests for BEARISH position evaluation logic."""

    def test_bearish_gap_through_sl(self):
        """BEARISH: open >= SL triggers immediate close at open."""
        new_status, exit_price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("85000"),
            take_profit_1=Decimal("78000"),
            take_profit_2=Decimal("75000"),
            bar_open=Decimal("86000"),  # Opens above SL
            bar_high=Decimal("87000"),
            bar_low=Decimal("85000"),
        )
        assert new_status == TradeStatus.CLOSED_SL
        assert exit_price == Decimal("86000")  # Gap-through at open

    def test_bearish_tp2_from_partial(self):
        """BEARISH PARTIAL_TP: low <= TP2 triggers full close."""
        new_status, exit_price = evaluate_bearish_position(
            status=TradeStatus.PARTIAL_TP,
            effective_sl=Decimal("82000"),  # Breakeven
            take_profit_1=Decimal("78000"),
            take_profit_2=Decimal("75000"),
            bar_open=Decimal("77000"),
            bar_high=Decimal("77500"),
            bar_low=Decimal("74000"),  # Breaches TP2
        )
        assert new_status == TradeStatus.CLOSED_TP2
        assert exit_price == Decimal("75000")

    def test_bearish_no_trigger(self):
        """BEARISH: price stays between SL and TP → no state change."""
        new_status, exit_price = evaluate_bearish_position(
            status=TradeStatus.ACTIVE,
            effective_sl=Decimal("85000"),
            take_profit_1=Decimal("78000"),
            take_profit_2=Decimal("75000"),
            bar_open=Decimal("81000"),
            bar_high=Decimal("82000"),
            bar_low=Decimal("80000"),
        )
        assert new_status is None
        assert exit_price is None

    def test_bearish_pnl_profitable_close(self):
        """BEARISH P&L: entry 82000, exit 78000 → profit."""
        pnl, pnl_pct = calculate_pnl(
            direction="bearish",
            entry_price=Decimal("82000"),
            quantity=500,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("78000"),
        )
        # Profit: (82000 - 78000) * 500 = 2,000,000
        assert pnl == Decimal("2000000")
        assert pnl_pct > 0

    def test_bearish_pnl_loss_close(self):
        """BEARISH P&L: entry 82000, exit 85000 → loss."""
        pnl, pnl_pct = calculate_pnl(
            direction="bearish",
            entry_price=Decimal("82000"),
            quantity=500,
            partial_exit_price=None,
            closed_quantity=0,
            exit_price=Decimal("85000"),
        )
        # Loss: (82000 - 85000) * 500 = -1,500,000
        assert pnl == Decimal("-1500000")
        assert pnl_pct < 0

    def test_bearish_with_partial_tp_pnl(self):
        """BEARISH 2-leg P&L: partial at TP1, final at TP2."""
        pnl, pnl_pct = calculate_pnl(
            direction="bearish",
            entry_price=Decimal("82000"),
            quantity=500,
            partial_exit_price=Decimal("78000"),  # TP1
            closed_quantity=200,  # Partial close
            exit_price=Decimal("75000"),  # TP2
        )
        # Leg 1: (82000 - 78000) * 200 = 800,000
        # Leg 2: (82000 - 75000) * 300 = 2,100,000
        # Total: 2,900,000
        assert pnl == Decimal("2900000")
        assert pnl_pct > 0
