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

    def test_portfolio_router_has_4_routes(self):
        """Portfolio router has POST trades, GET holdings, GET summary, GET trades."""
        from app.api.portfolio import router

        assert router.prefix == "/portfolio"
        assert len(router.routes) == 4

    def test_portfolio_included_in_main_router(self):
        """Portfolio router is included in the main api_router."""
        from app.api.router import api_router

        paths = [r.path for r in api_router.routes]
        assert "/portfolio/trades" in paths
        assert "/portfolio/holdings" in paths
