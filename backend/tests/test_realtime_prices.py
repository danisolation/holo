"""Tests for real-time price service — market hours, VCI polling, WebSocket manager.

TDD RED phase: tests written before implementation.
"""
import asyncio
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
        await service.poll_and_broadcast()

        mock_manager.broadcast.assert_called_once()
        call_arg = mock_manager.broadcast.call_args[0][0]
        assert "FPT" in call_arg

    @pytest.mark.asyncio
    async def test_poll_skips_when_no_subscribers(self):
        """Should not call crawler when no symbols subscribed."""
        from app.services.realtime_price_service import RealtimePriceService

        mock_crawler = AsyncMock()
        mock_manager = MagicMock()
        mock_manager.get_all_subscribed_symbols.return_value = set()
        mock_manager.broadcast = AsyncMock()

        service = RealtimePriceService(crawler=mock_crawler, connection_manager=mock_manager)
        await service.poll_and_broadcast()

        mock_crawler.fetch_price_board.assert_not_called()

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
        # Return 60 symbols (more than max 50)
        mock_manager.get_all_subscribed_symbols.return_value = {f"SYM{i}" for i in range(60)}
        mock_manager.broadcast = AsyncMock()

        service = RealtimePriceService(crawler=mock_crawler, connection_manager=mock_manager)
        await service.poll_and_broadcast()

        # Should have been called with at most 50 symbols
        call_args = mock_crawler.fetch_price_board.call_args[0][0]
        assert len(call_args) <= 50
