"""Tests for real-time price service — market hours, VCI polling, WebSocket manager.

TDD RED phase: tests written before implementation.
"""
import asyncio
import json
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from zoneinfo import ZoneInfo

import pytest
import pandas as pd

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


# ── Market hours tests ──────────────────────────────────────────────────────

class TestIsMarketOpen:
    """Test is_market_open() for various times and days."""

    def test_monday_morning_session_open(self):
        """9:30 on Monday should be open."""
        from app.services.realtime_price_service import is_market_open
        # Monday 9:30 AM VN time
        dt = datetime(2026, 4, 13, 9, 30, tzinfo=VN_TZ)  # Monday
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is True

    def test_monday_morning_session_start(self):
        """Exactly 9:00 should be open."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 9, 0, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is True

    def test_monday_morning_session_end(self):
        """11:30 should still be open (inclusive)."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 11, 30, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is True

    def test_monday_lunch_break_closed(self):
        """12:00 on Monday — lunch break, should be closed."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 12, 0, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is False

    def test_monday_afternoon_session_open(self):
        """13:30 on Monday — afternoon session, should be open."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 13, 30, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is True

    def test_monday_afternoon_session_end(self):
        """14:45 should still be open (inclusive)."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 14, 45, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is True

    def test_monday_after_market_closed(self):
        """15:00 on Monday — after market, should be closed."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 15, 0, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is False

    def test_saturday_closed(self):
        """Saturday should always be closed."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 18, 10, 0, tzinfo=VN_TZ)  # Saturday
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is False

    def test_sunday_closed(self):
        """Sunday should always be closed."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 19, 10, 0, tzinfo=VN_TZ)  # Sunday
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is False

    def test_early_morning_closed(self):
        """8:59 should be closed (before market)."""
        from app.services.realtime_price_service import is_market_open
        dt = datetime(2026, 4, 13, 8, 59, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert is_market_open() is False


class TestGetMarketSession:
    """Test get_market_session() returns correct session names."""

    def test_morning_session(self):
        from app.services.realtime_price_service import get_market_session
        dt = datetime(2026, 4, 13, 10, 0, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert get_market_session() == "morning"

    def test_afternoon_session(self):
        from app.services.realtime_price_service import get_market_session
        dt = datetime(2026, 4, 13, 14, 0, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert get_market_session() == "afternoon"

    def test_closed_session(self):
        from app.services.realtime_price_service import get_market_session
        dt = datetime(2026, 4, 13, 16, 0, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert get_market_session() == "closed"

    def test_lunch_break_closed(self):
        from app.services.realtime_price_service import get_market_session
        dt = datetime(2026, 4, 13, 12, 30, tzinfo=VN_TZ)
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert get_market_session() == "closed"

    def test_weekend_closed(self):
        from app.services.realtime_price_service import get_market_session
        dt = datetime(2026, 4, 18, 10, 0, tzinfo=VN_TZ)  # Saturday
        with patch("app.services.realtime_price_service._now_vn", return_value=dt):
            assert get_market_session() == "closed"


# ── VnstockCrawler.fetch_price_board tests ──────────────────────────────────

class TestFetchPriceBoard:
    """Test VnstockCrawler.fetch_price_board() with mocked Trading module."""

    @pytest.mark.asyncio
    async def test_fetch_price_board_returns_dict(self):
        """Should return dict keyed by symbol with price data."""
        from app.crawlers.vnstock_crawler import VnstockCrawler

        # Create mock DataFrame mimicking Trading.price_board output
        # MultiIndex columns: (listing, symbol), (match, match_price), etc.
        mock_df = pd.DataFrame({
            ("listing", "symbol"): ["VNM", "FPT"],
            ("match", "match_price"): [82500.0, 120000.0],
            ("match", "price_change"): [1500.0, -2000.0],
            ("match", "price_change_percent"): [1.85, -1.64],
            ("match", "total_volume"): [12345678, 9876543],
        })
        mock_df.columns = pd.MultiIndex.from_tuples(mock_df.columns)

        with patch("app.crawlers.vnstock_crawler.Trading") as MockTrading:
            mock_instance = MagicMock()
            mock_instance.price_board.return_value = mock_df
            MockTrading.return_value = mock_instance

            crawler = VnstockCrawler()
            result = await crawler.fetch_price_board(["VNM", "FPT"])

        assert isinstance(result, dict)
        assert "VNM" in result
        assert "FPT" in result
        assert result["VNM"]["price"] == 82500.0
        assert result["VNM"]["change"] == 1500.0
        assert result["VNM"]["change_pct"] == 1.85
        assert result["VNM"]["volume"] == 12345678
        assert result["FPT"]["price"] == 120000.0

    @pytest.mark.asyncio
    async def test_fetch_price_board_empty_symbols(self):
        """Should return empty dict when no symbols given."""
        from app.crawlers.vnstock_crawler import VnstockCrawler

        crawler = VnstockCrawler()
        result = await crawler.fetch_price_board([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_price_board_handles_api_error(self):
        """Should propagate errors from VCI API."""
        from app.crawlers.vnstock_crawler import VnstockCrawler

        with patch("app.crawlers.vnstock_crawler.Trading") as MockTrading:
            mock_instance = MagicMock()
            mock_instance.price_board.side_effect = ConnectionError("API down")
            MockTrading.return_value = mock_instance

            crawler = VnstockCrawler()
            with pytest.raises(ConnectionError):
                await crawler.fetch_price_board(["VNM"])


# ── RealtimePriceService tests ──────────────────────────────────────────────

class TestRealtimePriceService:
    """Test RealtimePriceService poll_and_broadcast + cache."""

    @pytest.mark.asyncio
    async def test_poll_updates_cache(self):
        """poll_and_broadcast should update internal price cache."""
        from app.services.realtime_price_service import RealtimePriceService

        mock_crawler = AsyncMock()
        mock_crawler.fetch_price_board.return_value = {
            "VNM": {"price": 82500, "change": 1500, "change_pct": 1.85, "volume": 123},
        }
        mock_manager = MagicMock()
        mock_manager.get_all_subscribed_symbols.return_value = {"VNM"}
        mock_manager.broadcast = AsyncMock()

        service = RealtimePriceService(crawler=mock_crawler, connection_manager=mock_manager)
        # Pre-load ticker map to avoid DB call
        service._ticker_map = {"VNM": 1}

        with patch("app.services.realtime_price_service.async_session") as mock_session_factory:
            mock_session_ctx = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await service.poll_and_broadcast()

        assert service.get_latest_prices(["VNM"]) == {
            "VNM": {"price": 82500, "change": 1500, "change_pct": 1.85, "volume": 123},
        }

    @pytest.mark.asyncio
    async def test_poll_broadcasts_to_manager(self):
        """poll_and_broadcast should call connection_manager.broadcast."""
        from app.services.realtime_price_service import RealtimePriceService

        mock_crawler = AsyncMock()
        mock_crawler.fetch_price_board.return_value = {
            "FPT": {"price": 120000, "change": -2000, "change_pct": -1.64, "volume": 456},
        }
        mock_manager = MagicMock()
        mock_manager.get_all_subscribed_symbols.return_value = {"FPT"}
        mock_manager.broadcast = AsyncMock()

        service = RealtimePriceService(crawler=mock_crawler, connection_manager=mock_manager)
        service._ticker_map = {"FPT": 2}

        with patch("app.services.realtime_price_service.async_session") as mock_session_factory:
            mock_session_ctx = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await service.poll_and_broadcast()

        mock_manager.broadcast.assert_called_once()
        call_arg = mock_manager.broadcast.call_args[0][0]
        assert "FPT" in call_arg

    @pytest.mark.asyncio
    async def test_poll_still_works_when_no_subscribers(self):
        """Should still poll all symbols even when no WS subscribers (intraday storage)."""
        from app.services.realtime_price_service import RealtimePriceService

        mock_crawler = AsyncMock()
        mock_crawler.fetch_price_board.return_value = {
            "VNM": {"price": 82500, "change": 0, "change_pct": 0, "volume": 100},
        }
        mock_manager = MagicMock()
        mock_manager.get_all_subscribed_symbols.return_value = set()
        mock_manager.broadcast = AsyncMock()

        service = RealtimePriceService(crawler=mock_crawler, connection_manager=mock_manager)
        service._ticker_map = {"VNM": 1}

        with patch("app.services.realtime_price_service.async_session") as mock_session_factory:
            mock_session_ctx = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await service.poll_and_broadcast()

        # Should have polled despite no subscribers
        mock_crawler.fetch_price_board.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_prices_filters(self):
        """get_latest_prices should return only requested symbols."""
        from app.services.realtime_price_service import RealtimePriceService

        service = RealtimePriceService(crawler=AsyncMock(), connection_manager=MagicMock())
        service._latest_prices = {
            "VNM": {"price": 82500},
            "FPT": {"price": 120000},
            "VIC": {"price": 50000},
        }

        result = service.get_latest_prices(["VNM", "VIC"])
        assert set(result.keys()) == {"VNM", "VIC"}
        assert "FPT" not in result

    @pytest.mark.asyncio
    async def test_poll_respects_max_symbols(self):
        """Should limit symbols to realtime_max_symbols config."""
        from app.services.realtime_price_service import RealtimePriceService

        mock_crawler = AsyncMock()
        mock_crawler.fetch_price_board.return_value = {}
        mock_manager = MagicMock()
        mock_manager.broadcast = AsyncMock()

        service = RealtimePriceService(crawler=mock_crawler, connection_manager=mock_manager)
        # Create 600 symbols in ticker map (more than max 500)
        service._ticker_map = {f"SYM{i:03d}": i for i in range(600)}

        with patch("app.services.realtime_price_service.async_session"):
            await service.poll_and_broadcast()

        # Should have been called with at most 500 symbols
        call_args = mock_crawler.fetch_price_board.call_args[0][0]
        assert len(call_args) <= 500


# ── ConnectionManager tests ─────────────────────────────────────────────────

class TestConnectionManager:
    """Test WebSocket ConnectionManager subscribe/unsubscribe/broadcast."""

    def _make_mock_ws(self):
        """Create a mock WebSocket with send_json async method."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_adds_client(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)
        assert ws in mgr._connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)
        mgr.disconnect(ws)
        assert ws not in mgr._connections

    @pytest.mark.asyncio
    async def test_subscribe_adds_symbols(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)
        mgr.subscribe(ws, ["VNM", "FPT"])
        assert mgr._connections[ws] == {"VNM", "FPT"}

    @pytest.mark.asyncio
    async def test_subscribe_appends_symbols(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)
        mgr.subscribe(ws, ["VNM"])
        mgr.subscribe(ws, ["FPT"])
        assert mgr._connections[ws] == {"VNM", "FPT"}

    def test_get_all_subscribed_symbols(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws1 = self._make_mock_ws()
        ws2 = self._make_mock_ws()
        mgr._connections[ws1] = {"VNM", "FPT"}
        mgr._connections[ws2] = {"FPT", "VIC"}
        assert mgr.get_all_subscribed_symbols() == {"VNM", "FPT", "VIC"}

    def test_get_all_subscribed_symbols_empty(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        assert mgr.get_all_subscribed_symbols() == set()

    @pytest.mark.asyncio
    async def test_broadcast_filters_by_subscription(self):
        """Each client should only receive prices for their subscribed symbols."""
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws1 = self._make_mock_ws()
        ws2 = self._make_mock_ws()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        mgr.subscribe(ws1, ["VNM"])
        mgr.subscribe(ws2, ["FPT"])

        prices = {
            "VNM": {"price": 82500},
            "FPT": {"price": 120000},
        }
        await mgr.broadcast(prices)

        # ws1 should get VNM only
        ws1.send_json.assert_called_once()
        sent1 = ws1.send_json.call_args[0][0]
        assert sent1["type"] == "price_update"
        assert "VNM" in sent1["data"]
        assert "FPT" not in sent1["data"]

        # ws2 should get FPT only
        ws2.send_json.assert_called_once()
        sent2 = ws2.send_json.call_args[0][0]
        assert sent2["type"] == "price_update"
        assert "FPT" in sent2["data"]
        assert "VNM" not in sent2["data"]

    @pytest.mark.asyncio
    async def test_broadcast_skips_clients_with_no_matching_symbols(self):
        """Client subscribed to symbols not in price update should not receive."""
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)
        mgr.subscribe(ws, ["VIC"])

        await mgr.broadcast({"VNM": {"price": 82500}})
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_heartbeat(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)

        await mgr.send_heartbeat()
        ws.send_json.assert_called_once_with({"type": "heartbeat"})

    @pytest.mark.asyncio
    async def test_send_market_status(self):
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws = self._make_mock_ws()
        await mgr.connect(ws)

        await mgr.send_market_status(is_open=True, session="morning")
        ws.send_json.assert_called_once_with({
            "type": "market_status",
            "is_open": True,
            "session": "morning",
        })

    @pytest.mark.asyncio
    async def test_broadcast_handles_dead_connection(self):
        """Dead WebSocket should be removed, not crash broadcast."""
        from app.ws.prices import ConnectionManager

        mgr = ConnectionManager()
        ws_live = self._make_mock_ws()
        ws_dead = self._make_mock_ws()
        ws_dead.send_json.side_effect = Exception("Connection closed")

        await mgr.connect(ws_live)
        await mgr.connect(ws_dead)
        mgr.subscribe(ws_live, ["VNM"])
        mgr.subscribe(ws_dead, ["VNM"])

        await mgr.broadcast({"VNM": {"price": 82500}})

        # Live client should still get data
        ws_live.send_json.assert_called_once()
        # Dead client should be removed
        assert ws_dead not in mgr._connections


# ── WebSocket endpoint integration test ──────────────────────────────────────

class TestWebSocketEndpoint:
    """Test /ws/prices endpoint via HTTPX/TestClient."""

    @pytest.mark.asyncio
    async def test_ws_endpoint_exists(self):
        """WebSocket route /ws/prices should be registered."""
        from app.main import app

        routes = [r.path for r in app.routes]
        assert "/ws/prices" in routes


# ── Scheduler job registration tests ────────────────────────────────────────

class TestSchedulerJobRegistration:
    """Test that realtime jobs are added to _JOB_NAMES."""

    def test_realtime_poll_job_in_names(self):
        from app.scheduler.manager import _JOB_NAMES
        assert "realtime_price_poll" in _JOB_NAMES

    def test_realtime_heartbeat_job_in_names(self):
        from app.scheduler.manager import _JOB_NAMES
        assert "realtime_heartbeat" in _JOB_NAMES
