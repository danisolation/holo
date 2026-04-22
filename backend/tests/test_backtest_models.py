"""Tests for Backtest model definitions.

Pure unit tests — no DB, no async. Validates enum values, model fields,
and column configurations.
"""
import pytest
from decimal import Decimal

from app.models.backtest import (
    BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis, BacktestStatus,
)
from app.models.paper_trade import TradeStatus, TradeDirection


class TestBacktestStatusEnum:
    def test_backtest_status_values(self):
        """BacktestStatus enum has 4 values: running, completed, cancelled, failed."""
        expected = {"running", "completed", "cancelled", "failed"}
        actual = {s.value for s in BacktestStatus}
        assert actual == expected

    def test_backtest_status_count(self):
        assert len(BacktestStatus) == 4

    def test_status_is_str_enum(self):
        """Enum values are strings (required for PostgreSQL native ENUM)."""
        assert isinstance(BacktestStatus.RUNNING, str)
        assert BacktestStatus.RUNNING == "running"


class TestBacktestRunModel:
    def test_tablename(self):
        assert BacktestRun.__tablename__ == "backtest_runs"

    def test_has_required_columns(self):
        """BacktestRun has all required columns."""
        columns = {c.name for c in BacktestRun.__table__.columns}
        required = {
            "id", "start_date", "end_date", "initial_capital", "slippage_pct",
            "status", "last_completed_date", "total_sessions", "completed_sessions",
            "is_cancelled", "created_at", "updated_at",
        }
        assert required.issubset(columns), f"Missing: {required - columns}"

    def test_initial_capital_default(self):
        """BacktestRun.initial_capital defaults to 100000000."""
        col = BacktestRun.__table__.columns["initial_capital"]
        assert str(col.server_default.arg) == "100000000"

    def test_slippage_pct_default(self):
        """BacktestRun.slippage_pct defaults to 0.5."""
        col = BacktestRun.__table__.columns["slippage_pct"]
        assert str(col.server_default.arg) == "0.5"

    def test_status_default(self):
        col = BacktestRun.__table__.columns["status"]
        assert str(col.server_default.arg) == "running"

    def test_total_sessions_default(self):
        col = BacktestRun.__table__.columns["total_sessions"]
        assert str(col.server_default.arg) == "0"

    def test_completed_sessions_default(self):
        col = BacktestRun.__table__.columns["completed_sessions"]
        assert str(col.server_default.arg) == "0"

    def test_is_cancelled_default(self):
        col = BacktestRun.__table__.columns["is_cancelled"]
        assert str(col.server_default.arg) == "false"

    def test_last_completed_date_nullable(self):
        col = BacktestRun.__table__.columns["last_completed_date"]
        assert col.nullable is True


class TestBacktestTradeModel:
    def test_tablename(self):
        assert BacktestTrade.__tablename__ == "backtest_trades"

    def test_has_required_columns(self):
        """BacktestTrade mirrors PaperTrade with added run_id and backtest_analysis_id."""
        columns = {c.name for c in BacktestTrade.__table__.columns}
        required = {
            "id", "run_id", "ticker_id", "backtest_analysis_id",
            "direction", "status",
            "entry_price", "stop_loss", "take_profit_1", "take_profit_2",
            "adjusted_stop_loss", "quantity", "closed_quantity",
            "realized_pnl", "realized_pnl_pct", "exit_price", "partial_exit_price",
            "signal_date", "entry_date", "closed_date",
            "confidence", "timeframe", "position_size_pct", "risk_reward_ratio",
            "created_at",
        }
        assert required.issubset(columns), f"Missing: {required - columns}"

    def test_run_id_not_nullable(self):
        col = BacktestTrade.__table__.columns["run_id"]
        assert col.nullable is False

    def test_backtest_analysis_id_nullable(self):
        col = BacktestTrade.__table__.columns["backtest_analysis_id"]
        assert col.nullable is True

    def test_status_default(self):
        col = BacktestTrade.__table__.columns["status"]
        assert str(col.server_default.arg) == "pending"

    def test_closed_quantity_default(self):
        col = BacktestTrade.__table__.columns["closed_quantity"]
        assert str(col.server_default.arg) == "0"

    def test_effective_stop_loss_returns_adjusted_when_set(self):
        """effective_stop_loss property returns adjusted_stop_loss when set, else stop_loss."""
        # Test the property logic directly — SQLAlchemy mapped instances need proper init
        assert hasattr(BacktestTrade, "effective_stop_loss")
        # Verify the property getter function logic
        class FakeTrade:
            stop_loss = Decimal("75000")
            adjusted_stop_loss = Decimal("80000")
        # Apply the property's fget to our fake
        result = BacktestTrade.effective_stop_loss.fget(FakeTrade())
        assert result == Decimal("80000")

    def test_effective_stop_loss_returns_original_when_no_adjusted(self):
        class FakeTrade:
            stop_loss = Decimal("75000")
            adjusted_stop_loss = None
        result = BacktestTrade.effective_stop_loss.fget(FakeTrade())
        assert result == Decimal("75000")


class TestBacktestAnalysisModel:
    def test_tablename(self):
        assert BacktestAnalysis.__tablename__ == "backtest_analyses"

    def test_has_required_columns(self):
        """BacktestAnalysis has run_id, ticker_id, analysis_type (String), etc."""
        columns = {c.name for c in BacktestAnalysis.__table__.columns}
        required = {
            "id", "run_id", "ticker_id", "analysis_type", "analysis_date",
            "signal", "score", "reasoning", "model_version", "raw_response",
            "created_at",
        }
        assert required.issubset(columns), f"Missing: {required - columns}"

    def test_analysis_type_is_string_not_enum(self):
        """Per RESEARCH.md A3: analysis_type is String(20), NOT Enum."""
        col = BacktestAnalysis.__table__.columns["analysis_type"]
        from sqlalchemy import String
        assert isinstance(col.type, String)

    def test_unique_constraint_exists(self):
        """UniqueConstraint on (run_id, ticker_id, analysis_type, analysis_date)."""
        constraint_names = [
            c.name for c in BacktestAnalysis.__table__.constraints
            if hasattr(c, 'name') and c.name
        ]
        assert "uq_backtest_analyses_run_ticker_type_date" in constraint_names

    def test_raw_response_nullable(self):
        col = BacktestAnalysis.__table__.columns["raw_response"]
        assert col.nullable is True


class TestBacktestEquityModel:
    def test_tablename(self):
        assert BacktestEquity.__tablename__ == "backtest_equity"

    def test_has_required_columns(self):
        """BacktestEquity has run_id, date, cash, positions_value, total_equity, returns."""
        columns = {c.name for c in BacktestEquity.__table__.columns}
        required = {
            "id", "run_id", "date", "cash", "positions_value", "total_equity",
            "daily_return_pct", "cumulative_return_pct",
        }
        assert required.issubset(columns), f"Missing: {required - columns}"

    def test_unique_constraint_exists(self):
        """UniqueConstraint on (run_id, date)."""
        constraint_names = [
            c.name for c in BacktestEquity.__table__.constraints
            if hasattr(c, 'name') and c.name
        ]
        assert "uq_backtest_equity_run_date" in constraint_names

    def test_daily_return_pct_nullable(self):
        col = BacktestEquity.__table__.columns["daily_return_pct"]
        assert col.nullable is True

    def test_cumulative_return_pct_nullable(self):
        col = BacktestEquity.__table__.columns["cumulative_return_pct"]
        assert col.nullable is True
