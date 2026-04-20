"""Tests for PaperTrade and SimulationConfig model definitions.

Pure unit tests — no DB, no async. Validates enum values, model fields,
and column configurations.
"""
import pytest
from app.models.paper_trade import PaperTrade, TradeStatus, TradeDirection


class TestTradeStatusEnum:
    def test_trade_status_values(self):
        """PT-02: All 7 lifecycle states exist."""
        expected = {"pending", "active", "partial_tp", "closed_tp2",
                    "closed_sl", "closed_timeout", "closed_manual"}
        actual = {s.value for s in TradeStatus}
        assert actual == expected

    def test_trade_status_count(self):
        assert len(TradeStatus) == 7

    def test_closed_states(self):
        """All terminal states start with 'closed'."""
        closed = [s for s in TradeStatus if s.value.startswith("closed")]
        assert len(closed) == 4

    def test_status_is_str_enum(self):
        """Enum values are strings (required for PostgreSQL native ENUM)."""
        assert isinstance(TradeStatus.PENDING, str)
        assert TradeStatus.PENDING == "pending"


class TestTradeDirectionEnum:
    def test_trade_direction_values(self):
        expected = {"long", "bearish"}
        actual = {d.value for d in TradeDirection}
        assert actual == expected

    def test_direction_count(self):
        assert len(TradeDirection) == 2


class TestPaperTradeModel:
    def test_tablename(self):
        assert PaperTrade.__tablename__ == "paper_trades"

    def test_has_required_columns(self):
        """PT-02: Model has all fields needed for paper trade lifecycle."""
        columns = {c.name for c in PaperTrade.__table__.columns}
        required = {
            "id", "ticker_id", "ai_analysis_id", "direction", "status",
            "entry_price", "stop_loss", "take_profit_1", "take_profit_2",
            "adjusted_stop_loss", "quantity", "closed_quantity",
            "realized_pnl", "realized_pnl_pct", "exit_price", "partial_exit_price",
            "signal_date", "entry_date", "closed_date",
            "confidence", "timeframe", "position_size_pct", "risk_reward_ratio",
            "created_at", "updated_at",
        }
        assert required.issubset(columns), f"Missing: {required - columns}"

    def test_ai_analysis_id_nullable(self):
        """ai_analysis_id is nullable for manual follows (Phase 24 prep)."""
        col = PaperTrade.__table__.columns["ai_analysis_id"]
        assert col.nullable is True

    def test_status_default(self):
        col = PaperTrade.__table__.columns["status"]
        assert str(col.server_default.arg) == "pending"

    def test_closed_quantity_default(self):
        col = PaperTrade.__table__.columns["closed_quantity"]
        assert str(col.server_default.arg) == "0"


class TestSimulationConfigModel:
    def test_tablename(self):
        from app.models.simulation_config import SimulationConfig
        assert SimulationConfig.__tablename__ == "simulation_config"

    def test_simulation_config_fields(self):
        """PT-05: SimulationConfig has initial_capital, auto_track, min_confidence."""
        from app.models.simulation_config import SimulationConfig
        columns = {c.name for c in SimulationConfig.__table__.columns}
        required = {"id", "initial_capital", "auto_track_enabled",
                    "min_confidence_threshold", "created_at", "updated_at"}
        assert required.issubset(columns), f"Missing: {required - columns}"

    def test_initial_capital_default(self):
        from app.models.simulation_config import SimulationConfig
        col = SimulationConfig.__table__.columns["initial_capital"]
        assert str(col.server_default.arg) == "100000000"

    def test_auto_track_default(self):
        from app.models.simulation_config import SimulationConfig
        col = SimulationConfig.__table__.columns["auto_track_enabled"]
        assert str(col.server_default.arg) == "true"

    def test_min_confidence_default(self):
        from app.models.simulation_config import SimulationConfig
        col = SimulationConfig.__table__.columns["min_confidence_threshold"]
        assert str(col.server_default.arg) == "5"
