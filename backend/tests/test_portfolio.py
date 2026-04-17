"""Tests for portfolio service: FIFO lot matching, P&L computation, trade recording.

Covers PORT-01 through PORT-07 requirements.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import date, datetime


# --- PORT-03: FIFO Lot Consumption Tests ---


class TestFIFO:
    """Test FIFO (first-in, first-out) lot consumption order."""

    @pytest.mark.asyncio
    async def test_fifo_consumes_oldest_lot_first(self):
        """Buy 100@10 then 100@20, sell 100 → should consume first lot (price 10)."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Two lots: older at price 10, newer at price 20
        lot1 = MagicMock()
        lot1.buy_price = Decimal("10")
        lot1.remaining_quantity = 100
        lot1.buy_date = date(2024, 1, 1)
        lot1.id = 1

        lot2 = MagicMock()
        lot2.buy_price = Decimal("20")
        lot2.remaining_quantity = 100
        lot2.buy_date = date(2024, 2, 1)
        lot2.id = 2

        # Mock _validate_sell to pass
        svc._validate_sell = AsyncMock()

        # Mock lot query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot1, lot2]
        svc.session.execute = AsyncMock(return_value=mock_result)

        realized = await svc._consume_lots_fifo(
            ticker_id=1,
            sell_qty=100,
            sell_price=Decimal("15"),
            sell_fees=Decimal("0"),
        )

        # Consumed lot1 (oldest): (15-10)*100 = 500
        assert realized == Decimal("500")
        assert lot1.remaining_quantity == 0
        assert lot2.remaining_quantity == 100  # untouched

    @pytest.mark.asyncio
    async def test_fifo_partial_consumption(self):
        """Buy 200@10, sell 150 → lot remaining = 50."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()
        svc._validate_sell = AsyncMock()

        lot = MagicMock()
        lot.buy_price = Decimal("10")
        lot.remaining_quantity = 200
        lot.buy_date = date(2024, 1, 1)
        lot.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        svc.session.execute = AsyncMock(return_value=mock_result)

        realized = await svc._consume_lots_fifo(
            ticker_id=1,
            sell_qty=150,
            sell_price=Decimal("15"),
            sell_fees=Decimal("0"),
        )

        assert realized == Decimal("750")  # (15-10)*150
        assert lot.remaining_quantity == 50

    @pytest.mark.asyncio
    async def test_fifo_multi_lot_consumption(self):
        """Buy 50@10, 50@20, sell 80 → lot1 fully consumed, lot2 remaining=20."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()
        svc._validate_sell = AsyncMock()

        lot1 = MagicMock()
        lot1.buy_price = Decimal("10")
        lot1.remaining_quantity = 50
        lot1.buy_date = date(2024, 1, 1)
        lot1.id = 1

        lot2 = MagicMock()
        lot2.buy_price = Decimal("20")
        lot2.remaining_quantity = 50
        lot2.buy_date = date(2024, 2, 1)
        lot2.id = 2

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot1, lot2]
        svc.session.execute = AsyncMock(return_value=mock_result)

        realized = await svc._consume_lots_fifo(
            ticker_id=1,
            sell_qty=80,
            sell_price=Decimal("25"),
            sell_fees=Decimal("0"),
        )

        # lot1: (25-10)*50 = 750, lot2: (25-20)*30 = 150 → 900
        assert realized == Decimal("900")
        assert lot1.remaining_quantity == 0
        assert lot2.remaining_quantity == 20


# --- PORT-04: Realized P&L Tests ---


class TestRealizedPnL:
    """Test realized P&L computation on sell trades."""

    @pytest.mark.asyncio
    async def test_realized_pnl_basic(self):
        """Buy 100@100, sell 100@150, fees=50 → realized = (150-100)*100 - 50 = 4950."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()
        svc._validate_sell = AsyncMock()

        lot = MagicMock()
        lot.buy_price = Decimal("100")
        lot.remaining_quantity = 100
        lot.buy_date = date(2024, 1, 1)
        lot.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        svc.session.execute = AsyncMock(return_value=mock_result)

        realized = await svc._consume_lots_fifo(
            ticker_id=1,
            sell_qty=100,
            sell_price=Decimal("150"),
            sell_fees=Decimal("50"),
        )

        assert realized == Decimal("4950")

    @pytest.mark.asyncio
    async def test_realized_pnl_multi_lot(self):
        """Buy 100@10, 100@20, sell 150@25 → (25-10)*100 + (25-20)*50 = 1750."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()
        svc._validate_sell = AsyncMock()

        lot1 = MagicMock()
        lot1.buy_price = Decimal("10")
        lot1.remaining_quantity = 100
        lot1.buy_date = date(2024, 1, 1)
        lot1.id = 1

        lot2 = MagicMock()
        lot2.buy_price = Decimal("20")
        lot2.remaining_quantity = 100
        lot2.buy_date = date(2024, 2, 1)
        lot2.id = 2

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot1, lot2]
        svc.session.execute = AsyncMock(return_value=mock_result)

        realized = await svc._consume_lots_fifo(
            ticker_id=1,
            sell_qty=150,
            sell_price=Decimal("25"),
            sell_fees=Decimal("0"),
        )

        assert realized == Decimal("1750")

    @pytest.mark.asyncio
    async def test_realized_pnl_fees_subtracted_from_pnl(self):
        """Per D-08-07: fees are subtracted from P&L, not cost basis."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()
        svc._validate_sell = AsyncMock()

        lot = MagicMock()
        lot.buy_price = Decimal("100")
        lot.remaining_quantity = 100
        lot.buy_date = date(2024, 1, 1)
        lot.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        svc.session.execute = AsyncMock(return_value=mock_result)

        # Without fees: (120-100)*100 = 2000
        realized_no_fees = await svc._consume_lots_fifo(
            ticker_id=1, sell_qty=100, sell_price=Decimal("120"), sell_fees=Decimal("0")
        )

        # Reset lot
        lot.remaining_quantity = 100
        realized_with_fees = await svc._consume_lots_fifo(
            ticker_id=1, sell_qty=100, sell_price=Decimal("120"), sell_fees=Decimal("100")
        )

        assert realized_no_fees == Decimal("2000")
        assert realized_with_fees == Decimal("1900")
        assert realized_no_fees - realized_with_fees == Decimal("100")


# --- D-08-06: Sell Validation Tests ---


class TestSellValidation:
    """Test sell validation prevents overselling."""

    @pytest.mark.asyncio
    async def test_sell_exceeds_available_raises_error(self):
        """Selling 200 with only 150 available → ValueError."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 150
        svc.session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot sell 200 shares — only 150 available"):
            await svc._validate_sell(ticker_id=1, sell_qty=200)

    @pytest.mark.asyncio
    async def test_sell_exact_amount_succeeds(self):
        """Selling exactly available amount → no error."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100
        svc.session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await svc._validate_sell(ticker_id=1, sell_qty=100)

    @pytest.mark.asyncio
    async def test_sell_zero_holdings_raises_error(self):
        """Selling with zero holdings → ValueError."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        svc.session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Cannot sell 50 shares — only 0 available"):
            await svc._validate_sell(ticker_id=1, sell_qty=50)


# --- PORT-01: Trade Recording Tests ---


class TestTradeRecording:
    """Test buy and sell trade recording flows."""

    @pytest.mark.asyncio
    async def test_buy_creates_trade_and_lot(self):
        """BUY trade should create Trade + Lot records."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock ticker resolution
        mock_ticker = MagicMock()
        mock_ticker.id = 1
        mock_ticker.symbol = "VNM"
        svc._resolve_ticker = AsyncMock(return_value=mock_ticker)

        # Mock flush to set trade.id
        async def mock_flush():
            for call in svc.session.add.call_args_list:
                obj = call[0][0]
                if hasattr(obj, "id") and obj.id is None:
                    obj.id = 1
                if hasattr(obj, "created_at") and obj.created_at is None:
                    obj.created_at = datetime(2024, 1, 15, 10, 0, 0)

        svc.session.flush = AsyncMock(side_effect=mock_flush)
        svc.session.commit = AsyncMock()

        result = await svc.record_trade(
            symbol="VNM", side="BUY", quantity=100,
            price=80000, trade_date=date(2024, 1, 15), fees=50
        )

        assert result["side"] == "BUY"
        assert result["quantity"] == 100
        assert result["price"] == 80000.0
        assert result["realized_pnl"] is None
        # Two adds: Trade + Lot
        assert svc.session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_sell_creates_trade_and_consumes_lots(self):
        """SELL trade should create Trade and consume lots via FIFO."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        mock_ticker = MagicMock()
        mock_ticker.id = 1
        mock_ticker.symbol = "VNM"
        svc._resolve_ticker = AsyncMock(return_value=mock_ticker)
        svc._consume_lots_fifo = AsyncMock(return_value=Decimal("5000"))

        async def mock_flush():
            for call in svc.session.add.call_args_list:
                obj = call[0][0]
                if hasattr(obj, "id") and obj.id is None:
                    obj.id = 2
                if hasattr(obj, "created_at") and obj.created_at is None:
                    obj.created_at = datetime(2024, 2, 15, 10, 0, 0)

        svc.session.flush = AsyncMock(side_effect=mock_flush)
        svc.session.commit = AsyncMock()

        result = await svc.record_trade(
            symbol="VNM", side="SELL", quantity=50,
            price=90000, trade_date=date(2024, 2, 15)
        )

        assert result["side"] == "SELL"
        assert result["realized_pnl"] == 5000.0
        # Only one add: Trade (no Lot for SELL)
        assert svc.session.add.call_count == 1

    @pytest.mark.asyncio
    async def test_unknown_ticker_raises_error(self):
        """Unknown ticker symbol → ValueError."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        svc.session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Ticker 'XYZ' not found"):
            await svc.record_trade(
                symbol="XYZ", side="BUY", quantity=100,
                price=10000, trade_date=date(2024, 1, 1)
            )


# --- API Endpoint and Schema Tests ---


class TestSchemaValidation:
    """Test Pydantic schema validation rules."""

    def test_trade_request_rejects_negative_quantity(self):
        """Quantity must be > 0."""
        from app.schemas.portfolio import TradeRequest

        with pytest.raises(Exception):
            TradeRequest(symbol="VNM", side="BUY", quantity=-1, price=80000, trade_date="2024-01-15")

    def test_trade_request_rejects_invalid_side(self):
        """Side must be BUY or SELL."""
        from app.schemas.portfolio import TradeRequest

        with pytest.raises(Exception):
            TradeRequest(symbol="VNM", side="HOLD", quantity=100, price=80000, trade_date="2024-01-15")

    def test_trade_request_accepts_valid_data(self):
        """Valid trade request passes validation."""
        from app.schemas.portfolio import TradeRequest

        req = TradeRequest(symbol="VNM", side="SELL", quantity=50, price=90000, trade_date="2024-01-15", fees=100)
        assert req.symbol == "VNM"
        assert req.side == "SELL"
        assert req.fees == 100

    def test_trade_request_default_fees_zero(self):
        """Fees default to 0 per D-08-07."""
        from app.schemas.portfolio import TradeRequest

        req = TradeRequest(symbol="VNM", side="BUY", quantity=100, price=80000, trade_date="2024-01-15")
        assert req.fees == 0


# --- PORT-08: Dividend Income Tests ---


class TestDividendIncome:
    """Test dividend income computation from CASH_DIVIDEND events."""

    @pytest.mark.asyncio
    async def test_dividend_income_basic(self):
        """1 CASH_DIVIDEND event (1500 VND/share), 1 lot with 200 remaining bought before record_date → 300000."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock CASH_DIVIDEND event
        event = MagicMock()
        event.event_type = "CASH_DIVIDEND"
        event.dividend_amount = Decimal("1500")
        event.record_date = date(2024, 6, 15)

        # Mock lot held before record_date
        lot = MagicMock()
        lot.remaining_quantity = 200
        lot.buy_date = date(2024, 1, 1)

        # session.execute called twice: first for events, then for lots
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event]

        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]

        svc.session.execute = AsyncMock(side_effect=[events_result, lots_result])

        result = await svc.get_dividend_income(ticker_id=1)
        assert result == 300000.0  # 1500 * 200

    @pytest.mark.asyncio
    async def test_dividend_income_multiple_events(self):
        """2 CASH_DIVIDEND events, lots held for both → sum of both."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        event1 = MagicMock()
        event1.event_type = "CASH_DIVIDEND"
        event1.dividend_amount = Decimal("1000")
        event1.record_date = date(2024, 3, 15)

        event2 = MagicMock()
        event2.event_type = "CASH_DIVIDEND"
        event2.dividend_amount = Decimal("2000")
        event2.record_date = date(2024, 6, 15)

        lot = MagicMock()
        lot.remaining_quantity = 100
        lot.buy_date = date(2024, 1, 1)

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event1, event2]

        lots_result1 = MagicMock()
        lots_result1.scalars.return_value.all.return_value = [lot]

        lots_result2 = MagicMock()
        lots_result2.scalars.return_value.all.return_value = [lot]

        svc.session.execute = AsyncMock(
            side_effect=[events_result, lots_result1, lots_result2]
        )

        result = await svc.get_dividend_income(ticker_id=1)
        # event1: 1000*100=100000, event2: 2000*100=200000 → 300000
        assert result == 300000.0

    @pytest.mark.asyncio
    async def test_dividend_income_no_events(self):
        """No CASH_DIVIDEND events → returns 0.0."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []
        svc.session.execute = AsyncMock(return_value=events_result)

        result = await svc.get_dividend_income(ticker_id=1)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_dividend_income_skips_lots_bought_after_record_date(self):
        """Lot bought AFTER record_date → not entitled, skipped."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        event = MagicMock()
        event.event_type = "CASH_DIVIDEND"
        event.dividend_amount = Decimal("1500")
        event.record_date = date(2024, 6, 15)

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event]

        # No lots match (all bought after record_date)
        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = []

        svc.session.execute = AsyncMock(side_effect=[events_result, lots_result])

        result = await svc.get_dividend_income(ticker_id=1)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_dividend_income_ignores_non_cash_events(self):
        """STOCK_DIVIDEND and BONUS_SHARES are filtered out by the query."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Only CASH_DIVIDEND events are returned by the query (service filters)
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []
        svc.session.execute = AsyncMock(return_value=events_result)

        result = await svc.get_dividend_income(ticker_id=1)
        assert result == 0.0


class TestHoldingsDividendAndSector:
    """Test that get_holdings includes dividend_income and sector fields."""

    @pytest.mark.asyncio
    async def test_holdings_includes_dividend_income(self):
        """Each holding should have a dividend_income field."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock lot aggregation query
        row = MagicMock()
        row.ticker_id = 1
        row.total_qty = 100
        row.avg_cost = Decimal("50000")
        row.total_cost = Decimal("5000000")

        agg_result = MagicMock()
        agg_result.all.return_value = [row]

        # Mock ticker query
        ticker = MagicMock()
        ticker.id = 1
        ticker.symbol = "VNM"
        ticker.name = "Vinamilk"
        ticker.sector = "Thực phẩm"

        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker

        # Mock latest price query
        price_result = MagicMock()
        price_result.scalar_one_or_none.return_value = Decimal("55000")

        svc.session.execute = AsyncMock(
            side_effect=[agg_result, ticker_result, price_result]
        )

        # Mock get_dividend_income
        svc.get_dividend_income = AsyncMock(return_value=150000.0)

        holdings = await svc.get_holdings()
        assert len(holdings) == 1
        assert holdings[0]["dividend_income"] == 150000.0

    @pytest.mark.asyncio
    async def test_holdings_includes_sector(self):
        """Each holding should have a sector field from Ticker model."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        row = MagicMock()
        row.ticker_id = 1
        row.total_qty = 100
        row.avg_cost = Decimal("50000")
        row.total_cost = Decimal("5000000")

        agg_result = MagicMock()
        agg_result.all.return_value = [row]

        ticker = MagicMock()
        ticker.id = 1
        ticker.symbol = "VNM"
        ticker.name = "Vinamilk"
        ticker.sector = "Thực phẩm"

        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker

        price_result = MagicMock()
        price_result.scalar_one_or_none.return_value = Decimal("55000")

        svc.session.execute = AsyncMock(
            side_effect=[agg_result, ticker_result, price_result]
        )

        svc.get_dividend_income = AsyncMock(return_value=0.0)

        holdings = await svc.get_holdings()
        assert len(holdings) == 1
        assert holdings[0]["sector"] == "Thực phẩm"


class TestSummaryDividendIncome:
    """Test that get_summary includes total dividend_income."""

    @pytest.mark.asyncio
    async def test_summary_includes_dividend_income(self):
        """Summary should aggregate dividend_income across all holdings."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock BUY total
        buy_result = MagicMock()
        buy_result.scalar_one.return_value = Decimal("10000000")

        # Mock SELL revenue
        sell_revenue_result = MagicMock()
        sell_revenue_result.scalar_one.return_value = Decimal("0")

        # Mock SELL fees
        sell_fees_result = MagicMock()
        sell_fees_result.scalar_one.return_value = Decimal("0")

        # Mock consumed cost
        consumed_cost_result = MagicMock()
        consumed_cost_result.scalar_one.return_value = Decimal("0")

        svc.session.execute = AsyncMock(
            side_effect=[buy_result, sell_revenue_result, sell_fees_result, consumed_cost_result]
        )

        # Mock get_holdings returning 2 holdings with dividend_income
        svc.get_holdings = AsyncMock(return_value=[
            {"market_value": 5500000, "unrealized_pnl": 500000, "dividend_income": 150000.0},
            {"market_value": 3200000, "unrealized_pnl": 200000, "dividend_income": 80000.0},
        ])

        summary = await svc.get_summary()
        assert summary["dividend_income"] == 230000.0  # 150000 + 80000


class TestAPIRouter:
    """Test API router registration."""

    def test_portfolio_router_has_9_routes(self):
        """Portfolio router has 9 routes: POST trades, GET holdings, GET summary,
        GET trades, GET performance, GET allocation, PUT trades/{id},
        DELETE trades/{id}, POST import."""
        from app.api.portfolio import router

        assert router.prefix == "/portfolio"
        assert len(router.routes) == 9

    def test_portfolio_included_in_main_router(self):
        """Portfolio router is included in the main api_router."""
        from app.api.router import api_router

        paths = [r.path for r in api_router.routes]
        assert "/portfolio/trades" in paths
        assert "/portfolio/holdings" in paths

    def test_new_portfolio_routes_registered(self):
        """New Phase 13 routes are registered."""
        from app.api.portfolio import router

        paths = [r.path for r in router.routes]
        assert "/portfolio/performance" in paths
        assert "/portfolio/allocation" in paths
        assert "/portfolio/import" in paths
        assert "/portfolio/trades/{trade_id}" in paths


# --- PORT-09: Performance Data Tests ---


class TestPerformanceData:
    """Test portfolio performance data computation."""

    @pytest.mark.asyncio
    async def test_performance_data_3m_returns_snapshots(self):
        """get_performance_data('3M') returns daily portfolio value snapshots for ~90 days."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock trade: BUY 100 VNM on 2024-01-10
        trade = MagicMock()
        trade.ticker_id = 1
        trade.side = "BUY"
        trade.quantity = 100
        trade.trade_date = date(2024, 1, 10)

        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = [trade]

        # Mock daily prices for 3 days
        price1 = MagicMock()
        price1.ticker_id = 1
        price1.date = date(2024, 1, 10)
        price1.close = Decimal("50000")

        price2 = MagicMock()
        price2.ticker_id = 1
        price2.date = date(2024, 1, 11)
        price2.close = Decimal("51000")

        price3 = MagicMock()
        price3.ticker_id = 1
        price3.date = date(2024, 1, 12)
        price3.close = Decimal("52000")

        prices_result = MagicMock()
        prices_result.all.return_value = [price1, price2, price3]

        svc.session.execute = AsyncMock(side_effect=[trades_result, prices_result])

        result = await svc.get_performance_data(period="3M")
        assert len(result) == 3
        assert result[0]["date"] == "2024-01-10"
        assert result[0]["value"] == 5000000.0  # 100 * 50000
        assert result[1]["value"] == 5100000.0  # 100 * 51000
        assert result[2]["value"] == 5200000.0  # 100 * 52000

    @pytest.mark.asyncio
    async def test_performance_data_no_trades_returns_empty(self):
        """get_performance_data with no trades → empty list."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = []
        svc.session.execute = AsyncMock(return_value=trades_result)

        result = await svc.get_performance_data(period="3M")
        assert result == []

    @pytest.mark.asyncio
    async def test_performance_data_handles_buy_and_sell(self):
        """BUY 200 on day 1, SELL 100 on day 2 → day 2 position = 100."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        trade1 = MagicMock()
        trade1.ticker_id = 1
        trade1.side = "BUY"
        trade1.quantity = 200
        trade1.trade_date = date(2024, 1, 10)

        trade2 = MagicMock()
        trade2.ticker_id = 1
        trade2.side = "SELL"
        trade2.quantity = 100
        trade2.trade_date = date(2024, 1, 11)

        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = [trade1, trade2]

        price1 = MagicMock()
        price1.ticker_id = 1
        price1.date = date(2024, 1, 10)
        price1.close = Decimal("50000")

        price2 = MagicMock()
        price2.ticker_id = 1
        price2.date = date(2024, 1, 11)
        price2.close = Decimal("55000")

        prices_result = MagicMock()
        prices_result.all.return_value = [price1, price2]

        svc.session.execute = AsyncMock(side_effect=[trades_result, prices_result])

        result = await svc.get_performance_data(period="3M")
        assert len(result) == 2
        # Day 1: BUY 200, value = 200 * 50000 = 10000000
        assert result[0]["value"] == 10000000.0
        # Day 2: SELL 100, position = 100, value = 100 * 55000 = 5500000
        assert result[1]["value"] == 5500000.0

    @pytest.mark.asyncio
    async def test_performance_data_1m_period(self):
        """get_performance_data('1M') should use ~30 day window."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        trade = MagicMock()
        trade.ticker_id = 1
        trade.side = "BUY"
        trade.quantity = 50
        trade.trade_date = date(2024, 1, 1)

        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = [trade]

        price = MagicMock()
        price.ticker_id = 1
        price.date = date(2024, 1, 10)
        price.close = Decimal("60000")

        prices_result = MagicMock()
        prices_result.all.return_value = [price]

        svc.session.execute = AsyncMock(side_effect=[trades_result, prices_result])

        result = await svc.get_performance_data(period="1M")
        assert len(result) == 1
        assert result[0]["value"] == 3000000.0  # 50 * 60000


# --- PORT-10: Allocation Data Tests ---


class TestAllocationData:
    """Test portfolio allocation data computation."""

    @pytest.mark.asyncio
    async def test_allocation_by_ticker(self):
        """get_allocation_data('ticker') returns per-ticker allocation."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        svc.get_holdings = AsyncMock(return_value=[
            {"symbol": "VNM", "market_value": 5000000, "sector": "Thực phẩm"},
            {"symbol": "FPT", "market_value": 3000000, "sector": "Công nghệ"},
        ])

        result = await svc.get_allocation_data(mode="ticker")
        assert len(result) == 2
        # Sorted by value descending
        assert result[0]["name"] == "VNM"
        assert result[0]["value"] == 5000000
        assert result[0]["percentage"] == 62.5  # 5M / 8M * 100
        assert result[1]["name"] == "FPT"
        assert result[1]["percentage"] == 37.5

    @pytest.mark.asyncio
    async def test_allocation_by_sector(self):
        """get_allocation_data('sector') groups holdings by sector."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        svc.get_holdings = AsyncMock(return_value=[
            {"symbol": "VNM", "market_value": 3000000, "sector": "Thực phẩm"},
            {"symbol": "MSN", "market_value": 2000000, "sector": "Thực phẩm"},
            {"symbol": "FPT", "market_value": 5000000, "sector": "Công nghệ"},
        ])

        result = await svc.get_allocation_data(mode="sector")
        assert len(result) == 2
        # Sorted by value descending: Thực phẩm=5M first then Công nghệ=5M? No: both equal
        # Actually: Thực phẩm=5M, Công nghệ=5M — equal, either order OK
        total = sum(r["value"] for r in result)
        assert total == 10000000
        # Check percentages sum to 100
        pct_sum = sum(r["percentage"] for r in result)
        assert pct_sum == 100.0

    @pytest.mark.asyncio
    async def test_allocation_by_sector_none_uses_default(self):
        """Holdings with no sector get grouped under 'Khác'."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        svc.get_holdings = AsyncMock(return_value=[
            {"symbol": "VNM", "market_value": 5000000, "sector": None},
        ])

        result = await svc.get_allocation_data(mode="sector")
        assert len(result) == 1
        assert result[0]["name"] == "Khác"
        assert result[0]["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_allocation_no_market_price_returns_empty(self):
        """Holdings without market_value → empty allocation."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        svc.get_holdings = AsyncMock(return_value=[
            {"symbol": "VNM", "market_value": None, "sector": "Thực phẩm"},
        ])

        result = await svc.get_allocation_data(mode="ticker")
        assert result == []


# --- PORT-11: Recalculate Lots + Trade Edit/Delete Tests ---


class TestRecalculateLots:
    """Test FIFO lot recalculation from trade history replay."""

    @pytest.mark.asyncio
    async def test_recalculate_lots_buy_only(self):
        """BUY trades only → creates lots with full remaining_quantity."""
        from app.services.portfolio_service import PortfolioService
        from app.models.lot import Lot
        from sqlalchemy import delete

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock trade: BUY 100 @ 50000 on 2024-01-10
        trade1 = MagicMock()
        trade1.id = 1
        trade1.ticker_id = 1
        trade1.side = "BUY"
        trade1.quantity = 100
        trade1.price = Decimal("50000")
        trade1.trade_date = date(2024, 1, 10)

        trade2 = MagicMock()
        trade2.id = 2
        trade2.ticker_id = 1
        trade2.side = "BUY"
        trade2.quantity = 200
        trade2.price = Decimal("55000")
        trade2.trade_date = date(2024, 2, 1)

        # session.execute: 1st call = delete lots, 2nd call = query trades
        delete_result = MagicMock()
        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = [trade1, trade2]

        svc.session.execute = AsyncMock(side_effect=[delete_result, trades_result])
        svc.session.flush = AsyncMock()

        added_objects = []
        svc.session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        await svc.recalculate_lots(ticker_id=1)

        # Should create 2 lots
        assert len(added_objects) == 2
        lot1 = added_objects[0]
        assert lot1.trade_id == 1
        assert lot1.quantity == 100
        assert lot1.remaining_quantity == 100
        assert lot1.buy_price == Decimal("50000")

        lot2 = added_objects[1]
        assert lot2.trade_id == 2
        assert lot2.quantity == 200
        assert lot2.remaining_quantity == 200

    @pytest.mark.asyncio
    async def test_recalculate_lots_buy_and_sell(self):
        """BUY + SELL trades → lots consumed correctly FIFO."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # BUY 100@50000 on Jan 10, BUY 100@55000 on Feb 1, SELL 120 on Mar 1
        trade1 = MagicMock()
        trade1.id = 1
        trade1.ticker_id = 1
        trade1.side = "BUY"
        trade1.quantity = 100
        trade1.price = Decimal("50000")
        trade1.trade_date = date(2024, 1, 10)

        trade2 = MagicMock()
        trade2.id = 2
        trade2.ticker_id = 1
        trade2.side = "BUY"
        trade2.quantity = 100
        trade2.price = Decimal("55000")
        trade2.trade_date = date(2024, 2, 1)

        trade3 = MagicMock()
        trade3.id = 3
        trade3.ticker_id = 1
        trade3.side = "SELL"
        trade3.quantity = 120
        trade3.price = Decimal("60000")
        trade3.trade_date = date(2024, 3, 1)

        delete_result = MagicMock()
        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = [trade1, trade2, trade3]

        svc.session.execute = AsyncMock(side_effect=[delete_result, trades_result])
        svc.session.flush = AsyncMock()

        added_objects = []
        svc.session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        await svc.recalculate_lots(ticker_id=1)

        # 2 lots created from BUY trades, then SELL 120 consumes FIFO
        assert len(added_objects) == 2
        lot1 = added_objects[0]
        lot2 = added_objects[1]

        # lot1: 100 bought, 100 consumed by SELL → remaining 0
        assert lot1.remaining_quantity == 0
        # lot2: 100 bought, 20 consumed by SELL → remaining 80
        assert lot2.remaining_quantity == 80

    @pytest.mark.asyncio
    async def test_recalculate_lots_no_trades(self):
        """No trades for ticker → deletes all lots, creates none."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        delete_result = MagicMock()
        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = []

        svc.session.execute = AsyncMock(side_effect=[delete_result, trades_result])
        svc.session.flush = AsyncMock()

        added_objects = []
        svc.session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        await svc.recalculate_lots(ticker_id=1)

        # No lots created
        assert len(added_objects) == 0

    @pytest.mark.asyncio
    async def test_recalculate_lots_sell_exceeds_available_raises(self):
        """SELL qty exceeds available BUY qty during replay → ValueError (T-13-03 mitigation)."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # BUY 50, SELL 100 → should raise
        trade1 = MagicMock()
        trade1.id = 1
        trade1.ticker_id = 1
        trade1.side = "BUY"
        trade1.quantity = 50
        trade1.price = Decimal("50000")
        trade1.trade_date = date(2024, 1, 10)

        trade2 = MagicMock()
        trade2.id = 2
        trade2.ticker_id = 1
        trade2.side = "SELL"
        trade2.quantity = 100
        trade2.price = Decimal("60000")
        trade2.trade_date = date(2024, 2, 1)

        delete_result = MagicMock()
        trades_result = MagicMock()
        trades_result.scalars.return_value.all.return_value = [trade1, trade2]

        svc.session.execute = AsyncMock(side_effect=[delete_result, trades_result])
        svc.session.flush = AsyncMock()

        added_objects = []
        svc.session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        with pytest.raises(ValueError, match="Cannot sell 100 shares"):
            await svc.recalculate_lots(ticker_id=1)


class TestUpdateTrade:
    """Test trade update with FIFO recalculation."""

    @pytest.mark.asyncio
    async def test_update_trade_changes_fields_and_recalculates(self):
        """update_trade modifies fields and triggers recalculate_lots."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock trade lookup
        trade = MagicMock()
        trade.id = 1
        trade.ticker_id = 1
        trade.side = "BUY"
        trade.quantity = 100
        trade.price = Decimal("50000")
        trade.fees = Decimal("0")
        trade.trade_date = date(2024, 1, 10)
        trade.created_at = datetime(2024, 1, 10, 10, 0, 0)

        trade_result = MagicMock()
        trade_result.scalar_one_or_none.return_value = trade

        # Mock ticker lookup for response
        ticker = MagicMock()
        ticker.symbol = "VNM"

        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker

        svc.session.execute = AsyncMock(side_effect=[trade_result, ticker_result])
        svc.session.commit = AsyncMock()

        # Mock recalculate_lots
        svc.recalculate_lots = AsyncMock()

        result = await svc.update_trade(
            trade_id=1,
            side="BUY",
            quantity=200,
            price=55000,
            trade_date=date(2024, 1, 15),
            fees=100,
        )

        # Verify trade fields updated
        assert trade.quantity == 200
        assert trade.price == Decimal("55000")
        assert trade.fees == Decimal("100")
        assert trade.trade_date == date(2024, 1, 15)

        # Verify recalculate_lots called
        svc.recalculate_lots.assert_awaited_once_with(1)

        # Verify response
        assert result["id"] == 1
        assert result["symbol"] == "VNM"
        assert result["quantity"] == 200

    @pytest.mark.asyncio
    async def test_update_trade_not_found_raises(self):
        """update_trade with non-existent trade ID → ValueError."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        trade_result = MagicMock()
        trade_result.scalar_one_or_none.return_value = None
        svc.session.execute = AsyncMock(return_value=trade_result)

        with pytest.raises(ValueError, match="Trade 999 not found"):
            await svc.update_trade(
                trade_id=999,
                side="BUY",
                quantity=100,
                price=50000,
                trade_date=date(2024, 1, 10),
            )


class TestDeleteTrade:
    """Test trade deletion with FIFO recalculation."""

    @pytest.mark.asyncio
    async def test_delete_trade_removes_and_recalculates(self):
        """delete_trade removes trade and triggers recalculate_lots."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # Mock trade lookup
        trade = MagicMock()
        trade.id = 1
        trade.ticker_id = 1

        trade_result = MagicMock()
        trade_result.scalar_one_or_none.return_value = trade
        svc.session.execute = AsyncMock(return_value=trade_result)
        svc.session.delete = AsyncMock()
        svc.session.flush = AsyncMock()
        svc.session.commit = AsyncMock()

        # Mock recalculate_lots
        svc.recalculate_lots = AsyncMock()

        result = await svc.delete_trade(trade_id=1)

        # Verify trade deleted
        svc.session.delete.assert_awaited_once_with(trade)

        # Verify recalculate_lots called
        svc.recalculate_lots.assert_awaited_once_with(1)

        # Verify response
        assert result["deleted"] is True
        assert result["trade_id"] == 1

    @pytest.mark.asyncio
    async def test_delete_trade_not_found_raises(self):
        """delete_trade with non-existent trade ID → ValueError."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        trade_result = MagicMock()
        trade_result.scalar_one_or_none.return_value = None
        svc.session.execute = AsyncMock(return_value=trade_result)

        with pytest.raises(ValueError, match="Trade 999 not found"):
            await svc.delete_trade(trade_id=999)

    @pytest.mark.asyncio
    async def test_delete_sell_trade_restores_lots(self):
        """Delete a SELL trade → recalculate_lots restores lots to pre-sell state."""
        from app.services.portfolio_service import PortfolioService

        svc = PortfolioService.__new__(PortfolioService)
        svc.session = AsyncMock()

        # The SELL trade to be deleted
        sell_trade = MagicMock()
        sell_trade.id = 2
        sell_trade.ticker_id = 1
        sell_trade.side = "SELL"

        trade_result = MagicMock()
        trade_result.scalar_one_or_none.return_value = sell_trade
        svc.session.execute = AsyncMock(return_value=trade_result)
        svc.session.delete = AsyncMock()
        svc.session.flush = AsyncMock()
        svc.session.commit = AsyncMock()

        # Mock recalculate_lots - after delete, only BUY trades remain
        svc.recalculate_lots = AsyncMock()

        result = await svc.delete_trade(trade_id=2)

        assert result["deleted"] is True
        # recalculate_lots is called, which will replay only BUY trades
        # This ensures lots are restored to pre-sell state
        svc.recalculate_lots.assert_awaited_once_with(1)
