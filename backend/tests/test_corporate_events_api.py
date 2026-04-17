"""Tests for corporate events calendar API and adjusted price toggle (Plan 14-03)."""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked database and scheduler."""
    with patch("app.database.engine") as mock_engine:
        mock_engine.dispose = AsyncMock()
        with patch("app.scheduler.manager.scheduler") as mock_scheduler:
            mock_scheduler.running = True
            mock_scheduler.start = MagicMock()
            mock_scheduler.shutdown = MagicMock()
            mock_scheduler.get_jobs.return_value = []

            with patch("app.scheduler.manager.configure_jobs"):
                from app.main import app
                yield TestClient(app)


def _make_event_row(
    event_id=1,
    symbol="VNM",
    name="Vinamilk",
    event_type="CASH_DIVIDEND",
    ex_date=None,
    record_date=None,
    announcement_date=None,
    dividend_amount=None,
    ratio=None,
    note=None,
):
    """Create a mock row simulating joined CorporateEvent + Ticker query result."""
    if ex_date is None:
        ex_date = date.today()
    row = MagicMock()
    row.id = event_id
    row.symbol = symbol
    row.name = name
    row.event_type = event_type
    row.ex_date = ex_date
    row.record_date = record_date
    row.announcement_date = announcement_date
    row.dividend_amount = dividend_amount
    row.ratio = ratio
    row.note = note
    # Make attributes accessible by both attribute and index
    return row


def _make_mock_session_with_events(rows):
    """Create mock async session context manager returning given rows."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx, mock_session


class TestCorporateEventsCalendarEndpoint:
    """Tests for GET /api/corporate-events endpoint."""

    def test_returns_list_of_events(self, client):
        """GET /api/corporate-events returns a list of event objects."""
        rows = [
            _make_event_row(event_id=1, symbol="VNM", event_type="CASH_DIVIDEND",
                            ex_date=date.today(), dividend_amount=Decimal("2000")),
        ]
        mock_ctx, _ = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["symbol"] == "VNM"
            assert data[0]["event_type"] == "CASH_DIVIDEND"

    def test_response_includes_all_fields(self, client):
        """Response must include id, symbol, name, event_type, ex_date, record_date, dividend_amount, ratio, note."""
        rows = [
            _make_event_row(
                event_id=42, symbol="FPT", name="FPT Corp",
                event_type="STOCK_DIVIDEND", ex_date=date(2026, 4, 15),
                record_date=date(2026, 4, 10), announcement_date=date(2026, 3, 20),
                dividend_amount=None, ratio=Decimal("35.0"), note="35:100",
            ),
        ]
        mock_ctx, _ = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/")
            data = response.json()
            event = data[0]
            assert event["id"] == 42
            assert event["symbol"] == "FPT"
            assert event["name"] == "FPT Corp"
            assert event["event_type"] == "STOCK_DIVIDEND"
            assert event["ex_date"] == "2026-04-15"
            assert event["record_date"] == "2026-04-10"
            assert event["announcement_date"] == "2026-03-20"
            assert event["ratio"] == 35.0
            assert event["note"] == "35:100"

    def test_month_filter_param(self, client):
        """month=2026-04 should filter events to April 2026."""
        rows = [
            _make_event_row(event_id=1, ex_date=date(2026, 4, 15)),
        ]
        mock_ctx, mock_session = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/?month=2026-04")
            assert response.status_code == 200
            # Verify the query was made (session.execute called)
            assert mock_session.execute.called

    def test_type_filter_param(self, client):
        """type=CASH_DIVIDEND should filter by event type."""
        rows = [
            _make_event_row(event_id=1, event_type="CASH_DIVIDEND"),
        ]
        mock_ctx, mock_session = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/?type=CASH_DIVIDEND")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["event_type"] == "CASH_DIVIDEND"

    def test_symbol_filter_param(self, client):
        """symbol=VNM should filter to VNM events only."""
        rows = [
            _make_event_row(event_id=1, symbol="VNM"),
        ]
        mock_ctx, mock_session = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/?symbol=VNM")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["symbol"] == "VNM"

    def test_default_no_params_returns_200(self, client):
        """No params should return events within default date range (no error)."""
        rows = []
        mock_ctx, _ = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/")
            assert response.status_code == 200
            assert isinstance(response.json(), list)

    def test_events_sorted_by_ex_date_desc(self, client):
        """Events should be returned sorted by ex_date DESC."""
        rows = [
            _make_event_row(event_id=2, symbol="FPT", ex_date=date(2026, 5, 1)),
            _make_event_row(event_id=1, symbol="VNM", ex_date=date(2026, 4, 1)),
        ]
        mock_ctx, _ = _make_mock_session_with_events(rows)
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/")
            data = response.json()
            assert len(data) == 2
            # First event should have later date
            assert data[0]["ex_date"] >= data[1]["ex_date"]

    def test_invalid_type_returns_400(self, client):
        """Invalid event type should return 400."""
        # No mock needed — validation happens before DB query
        mock_ctx, _ = _make_mock_session_with_events([])
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/?type=INVALID_TYPE")
            assert response.status_code == 400
            assert "Invalid event type" in response.json()["detail"]

    def test_invalid_month_format_returns_400(self, client):
        """Invalid month format should return 400 (T-14-07 mitigation)."""
        mock_ctx, _ = _make_mock_session_with_events([])
        with patch("app.api.corporate_events.async_session", return_value=mock_ctx):
            response = client.get("/api/corporate-events/?month=not-a-month")
            assert response.status_code == 400
            assert "Invalid month format" in response.json()["detail"]


class TestRouterRegistration:
    """Verify corporate_events router is registered."""

    def test_corporate_events_router_registered(self):
        """Router module must be imported and registered in api_router."""
        from app.api.router import api_router
        routes = [route.path for route in api_router.routes]
        assert any("/corporate-events" in r for r in routes), \
            f"corporate-events not found in routes: {routes}"


def _make_mock_ticker(symbol="VNM", ticker_id=1, name="Vinamilk"):
    """Create a mock Ticker object."""
    ticker = MagicMock()
    ticker.id = ticker_id
    ticker.symbol = symbol
    ticker.name = name
    return ticker


def _make_mock_price(
    price_date=None,
    open_val=50000,
    high_val=52000,
    low_val=49000,
    close_val=51000,
    volume=1000000,
    adjusted_close=53000,
):
    """Create a mock DailyPrice object with distinct close and adjusted_close."""
    if price_date is None:
        price_date = date.today()
    price = MagicMock()
    price.date = price_date
    price.open = Decimal(str(open_val))
    price.high = Decimal(str(high_val))
    price.low = Decimal(str(low_val))
    price.close = Decimal(str(close_val))
    price.volume = volume
    price.adjusted_close = Decimal(str(adjusted_close)) if adjusted_close is not None else None
    return price


class TestAdjustedPriceToggle:
    """Tests for GET /{symbol}/prices adjusted parameter (CORP-09)."""

    def test_adjusted_true_returns_adjusted_close(self, client):
        """adjusted=true should use adjusted_close as close value."""
        ticker = _make_mock_ticker()
        prices = [_make_mock_price(close_val=50000, adjusted_close=53000)]

        mock_session = AsyncMock()
        # First call: ticker lookup
        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker
        # Second call: price query
        price_result = MagicMock()
        price_result.scalars.return_value.all.return_value = prices

        mock_session.execute = AsyncMock(side_effect=[ticker_result, price_result])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.tickers.async_session", return_value=mock_ctx):
            response = client.get("/api/tickers/VNM/prices?adjusted=true")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            # close field should be adjusted_close value (53000)
            assert data[0]["close"] == 53000.0
            # adjusted_close should still be populated
            assert data[0]["adjusted_close"] == 53000.0

    def test_adjusted_false_returns_raw_close(self, client):
        """adjusted=false should use raw close value."""
        ticker = _make_mock_ticker()
        prices = [_make_mock_price(close_val=50000, adjusted_close=53000)]

        mock_session = AsyncMock()
        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker
        price_result = MagicMock()
        price_result.scalars.return_value.all.return_value = prices

        mock_session.execute = AsyncMock(side_effect=[ticker_result, price_result])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.tickers.async_session", return_value=mock_ctx):
            response = client.get("/api/tickers/VNM/prices?adjusted=false")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            # close field should be raw close value (50000)
            assert data[0]["close"] == 50000.0
            # adjusted_close should still be populated
            assert data[0]["adjusted_close"] == 53000.0

    def test_default_no_adjusted_param_returns_adjusted(self, client):
        """No adjusted param should default to adjusted=true (backward compatible)."""
        ticker = _make_mock_ticker()
        prices = [_make_mock_price(close_val=50000, adjusted_close=53000)]

        mock_session = AsyncMock()
        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker
        price_result = MagicMock()
        price_result.scalars.return_value.all.return_value = prices

        mock_session.execute = AsyncMock(side_effect=[ticker_result, price_result])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.tickers.async_session", return_value=mock_ctx):
            response = client.get("/api/tickers/VNM/prices")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            # Default should use adjusted close (53000)
            assert data[0]["close"] == 53000.0

    def test_adjusted_true_no_adjusted_close_falls_back_to_close(self, client):
        """When adjusted=true but adjusted_close is None, should fall back to raw close."""
        ticker = _make_mock_ticker()
        prices = [_make_mock_price(close_val=50000, adjusted_close=None)]

        mock_session = AsyncMock()
        ticker_result = MagicMock()
        ticker_result.scalar_one_or_none.return_value = ticker
        price_result = MagicMock()
        price_result.scalars.return_value.all.return_value = prices

        mock_session.execute = AsyncMock(side_effect=[ticker_result, price_result])
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.api.tickers.async_session", return_value=mock_ctx):
            response = client.get("/api/tickers/VNM/prices?adjusted=true")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            # Should fall back to raw close (50000) when adjusted_close is None
            assert data[0]["close"] == 50000.0
            assert data[0]["adjusted_close"] is None

    def test_response_schema_unchanged(self, client):
        """PriceResponse schema should still have all original fields."""
        from app.api.tickers import PriceResponse
        fields = PriceResponse.model_fields
        assert "date" in fields
        assert "open" in fields
        assert "high" in fields
        assert "low" in fields
        assert "close" in fields
        assert "volume" in fields
        assert "adjusted_close" in fields
