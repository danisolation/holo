"""Tests for dual portfolio routing logic.

Phase 107: Verifies that AI and user portfolios are independently scoped,
AutoTradeService targets AI portfolio, and schema validation works.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.simulator_service import SimulatorService


class TestGetOrCreatePortfolio:
    """Test that get_or_create_portfolio routes by name."""

    def test_default_name_is_user(self):
        """Default portfolio name should be 'user' for backward compat."""
        import inspect
        sig = inspect.signature(SimulatorService.get_or_create_portfolio)
        assert sig.parameters["name"].default == "user"

    def test_create_trade_default_is_user(self):
        """create_trade default portfolio should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.create_trade)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_get_portfolio_default_is_user(self):
        """get_portfolio default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.get_portfolio)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_list_trades_default_is_user(self):
        """list_trades default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.list_trades)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_get_stats_default_is_user(self):
        """get_stats default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.get_stats)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_get_equity_history_default_is_user(self):
        """get_equity_history default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.get_equity_history)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_get_pnl_timeline_default_is_user(self):
        """get_pnl_timeline default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.get_pnl_timeline)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_reset_portfolio_default_is_user(self):
        """reset_portfolio default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.reset_portfolio)
        assert sig.parameters["portfolio_name"].default == "user"

    def test_check_sl_tp_hits_default_is_user(self):
        """check_sl_tp_hits default should be 'user'."""
        import inspect
        sig = inspect.signature(SimulatorService.check_sl_tp_hits)
        assert sig.parameters["portfolio_name"].default == "user"


class TestPortfolioTypeValidation:
    """Test portfolio_type values."""

    def test_valid_portfolio_types(self):
        from app.schemas.simulator import SimulatorTradeCreate
        from datetime import date

        # "user" default
        trade = SimulatorTradeCreate(
            ticker_symbol="VNM", side="BUY", quantity=100,
            price=100000, trade_date=date.today()
        )
        assert trade.portfolio_type == "user"

        # "ai" explicit
        trade_ai = SimulatorTradeCreate(
            ticker_symbol="VNM", side="BUY", quantity=100,
            price=100000, trade_date=date.today(), portfolio_type="ai"
        )
        assert trade_ai.portfolio_type == "ai"

    def test_invalid_portfolio_type_rejected(self):
        from app.schemas.simulator import SimulatorTradeCreate
        from datetime import date
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SimulatorTradeCreate(
                ticker_symbol="VNM", side="BUY", quantity=100,
                price=100000, trade_date=date.today(), portfolio_type="invalid"
            )

    def test_source_default_is_manual(self):
        from app.schemas.simulator import SimulatorTradeCreate
        from datetime import date

        trade = SimulatorTradeCreate(
            ticker_symbol="VNM", side="BUY", quantity=100,
            price=100000, trade_date=date.today()
        )
        assert trade.source == "manual"


class TestAutoTradeServiceTargetsAI:
    """Verify AutoTradeService always targets AI portfolio."""

    def test_execute_ai_signals_uses_ai_portfolio(self):
        """execute_ai_signals should pass portfolio_name='ai' to create_trade."""
        import inspect
        from app.services.auto_trade_service import AutoTradeService
        source = inspect.getsource(AutoTradeService.execute_ai_signals)
        assert 'portfolio_name="ai"' in source or "portfolio_name='ai'" in source

    def test_execute_sell_signals_uses_ai_portfolio(self):
        """execute_sell_signals should get AI portfolio."""
        import inspect
        from app.services.auto_trade_service import AutoTradeService
        source = inspect.getsource(AutoTradeService.execute_sell_signals)
        assert '"ai"' in source or "'ai'" in source

    def test_execute_sell_signals_creates_trade_with_ai(self):
        """execute_sell_signals create_trade call should use portfolio_name='ai'."""
        import inspect
        from app.services.auto_trade_service import AutoTradeService
        source = inspect.getsource(AutoTradeService.execute_sell_signals)
        assert 'portfolio_name="ai"' in source


class TestPortfolioListResponseSchema:
    """Test PortfolioListResponse schema."""

    def test_portfolio_summary_item_fields(self):
        from app.schemas.simulator import PortfolioSummaryItem
        item = PortfolioSummaryItem(
            name="ai",
            starting_capital=100000000.0,
            current_cash=99000000.0,
            total_equity=99500000.0,
            total_pnl=-500000.0,
            total_pnl_pct=-0.5,
            position_count=2,
        )
        assert item.name == "ai"
        assert item.position_count == 2

    def test_portfolio_list_response(self):
        from app.schemas.simulator import PortfolioListResponse, PortfolioSummaryItem
        response = PortfolioListResponse(
            portfolios=[
                PortfolioSummaryItem(
                    name="ai", starting_capital=100000000.0, current_cash=100000000.0,
                    total_equity=100000000.0, total_pnl=0.0, total_pnl_pct=0.0, position_count=0,
                ),
                PortfolioSummaryItem(
                    name="user", starting_capital=100000000.0, current_cash=100000000.0,
                    total_equity=100000000.0, total_pnl=0.0, total_pnl_pct=0.0, position_count=0,
                ),
            ]
        )
        assert len(response.portfolios) == 2


class TestSchedulerAutoBuyImport:
    """Verify auto-buy job is importable from scheduler."""

    def test_daily_simulator_auto_buy_importable(self):
        from app.scheduler.jobs import daily_simulator_auto_buy
        import asyncio
        assert asyncio.iscoroutinefunction(daily_simulator_auto_buy)
