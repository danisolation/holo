"""Tests for VNDirect WebSocket client — message parsing and lifecycle logic."""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.services.vndirect_ws_client import (
    VNDirectWSClient,
    parse_sp_message,
    parse_ba_message,
    _try_float,
)


# ─── parse_sp_message tests ─────────────────────────────────────────────────


class TestParseSPMessage:
    """Test SP (Stock Price) message parsing."""

    VALID_SP = (
        "HOSE|2025-01-15|10:30:00|VNM|Vinamilk|S|1000000|500000"
        "|82000|83000|82500|84000|15000|85000|81000|87500|79500"
        "|83500|125000000000|10000|5000|0|12345"
    )

    def test_valid_sp_message(self):
        result = parse_sp_message(self.VALID_SP)
        assert result is not None
        assert result["symbol"] == "VNM"
        assert result["price"] == 84000.0  # currentPrice (index 11)
        assert result["ref_price"] == 82000.0  # basicPrice (index 8)
        assert result["open"] == 83000.0
        assert result["high"] == 85000.0
        assert result["low"] == 81000.0
        assert result["ceiling"] == 87500.0
        assert result["floor"] == 79500.0
        assert result["volume"] == 15000.0  # currentQtty (match volume)
        # change = 84000 - 82000 = 2000
        assert result["change"] == 2000.0
        # change_pct = 2000/82000*100 ≈ 2.44
        assert abs(result["change_pct"] - 2.44) < 0.01

    def test_none_input(self):
        assert parse_sp_message(None) is None

    def test_empty_string(self):
        assert parse_sp_message("") is None

    def test_too_few_fields(self):
        assert parse_sp_message("A|B|C|D|E") is None

    def test_missing_symbol(self):
        # symbol field (index 3) is empty
        raw = "|".join(["X"] * 3 + [""] + ["X"] * 19)
        assert parse_sp_message(raw) is None

    def test_non_numeric_prices_return_zero(self):
        # Replace numeric fields with non-numeric
        fields = ["HOSE", "2025-01-15", "10:00:00", "FPT", "FPT Corp", "S",
                  "abc", "def", "ghi", "jkl", "mno", "pqr", "stu",
                  "vwx", "yza", "bcd", "efg", "hij", "klm", "nop",
                  "qrs", "tuv", "seq1"]
        raw = "|".join(fields)
        result = parse_sp_message(raw)
        assert result is not None
        assert result["symbol"] == "FPT"
        assert result["price"] == 0.0
        assert result["change"] == 0.0

    def test_ref_price_zero_no_division_error(self):
        fields = ["HOSE", "2025-01-15", "10:00:00", "HPG", "Hoa Phat", "S",
                  "100", "50", "0", "50000", "49000", "51000", "1000",
                  "52000", "48000", "55000", "45000", "50500", "1000000",
                  "200", "100", "0", "999"]
        raw = "|".join(fields)
        result = parse_sp_message(raw)
        assert result is not None
        assert result["change"] == 0.0  # ref_price=0 means no meaningful change
        assert result["change_pct"] == 0.0  # no division by zero


# ─── parse_ba_message tests ──────────────────────────────────────────────────


class TestParseBAMessage:
    """Test BA (Bid/Ask) message parsing."""

    VALID_BA = (
        "10:30:00|VNM"
        "|83900|5000|83800|3000|83700|2000"
        "|84100|4000|84200|2500|84300|1500"
        "|500000|84000|1000|84000000|15000|12000"
    )

    def test_valid_ba_message(self):
        result = parse_ba_message(self.VALID_BA)
        assert result is not None
        assert result["symbol"] == "VNM"
        assert len(result["bids"]) == 3
        assert len(result["asks"]) == 3
        # Bid 1 (best bid)
        assert result["bids"][0] == {"price": 83900.0, "volume": 5000.0}
        assert result["bids"][1] == {"price": 83800.0, "volume": 3000.0}
        assert result["bids"][2] == {"price": 83700.0, "volume": 2000.0}
        # Ask 1 (best ask)
        assert result["asks"][0] == {"price": 84100.0, "volume": 4000.0}
        assert result["asks"][1] == {"price": 84200.0, "volume": 2500.0}
        assert result["asks"][2] == {"price": 84300.0, "volume": 1500.0}
        assert result["match_price"] == 84000.0
        assert result["total_bid_volume"] == 12000.0
        assert result["total_ask_volume"] == 15000.0

    def test_none_input(self):
        assert parse_ba_message(None) is None

    def test_empty_string(self):
        assert parse_ba_message("") is None

    def test_too_few_fields(self):
        assert parse_ba_message("10:30:00|VNM|100|200") is None

    def test_missing_symbol(self):
        fields = ["10:30:00", ""] + ["100"] * 18
        raw = "|".join(fields)
        assert parse_ba_message(raw) is None

    def test_non_numeric_returns_zero(self):
        fields = ["10:30:00", "HPG"] + ["abc"] * 18
        raw = "|".join(fields)
        result = parse_ba_message(raw)
        assert result is not None
        assert result["bids"][0] == {"price": 0.0, "volume": 0.0}


# ─── VNDirectWSClient lifecycle tests ────────────────────────────────────────


class TestVNDirectWSClientBackoff:
    """Test exponential backoff calculation."""

    def test_attempt_0(self):
        assert VNDirectWSClient._calculate_backoff(0) == 1.0

    def test_attempt_1(self):
        assert VNDirectWSClient._calculate_backoff(1) == 2.0

    def test_attempt_2(self):
        assert VNDirectWSClient._calculate_backoff(2) == 4.0

    def test_attempt_5(self):
        assert VNDirectWSClient._calculate_backoff(5) == 32.0

    def test_attempt_6(self):
        assert VNDirectWSClient._calculate_backoff(6) == 60.0  # capped

    def test_attempt_7(self):
        assert VNDirectWSClient._calculate_backoff(7) == 60.0  # capped

    def test_attempt_100(self):
        assert VNDirectWSClient._calculate_backoff(100) == 60.0  # capped


class TestVNDirectWSClientMarketHours:
    """Test market hours enforcement."""

    def _make_client(self):
        return VNDirectWSClient(
            symbols=["VNM", "FPT"],
            on_price_update=AsyncMock(),
        )

    @patch("app.services.vndirect_ws_client.is_market_open")
    def test_should_connect_market_open(self, mock_market):
        mock_market.return_value = True
        client = self._make_client()
        assert client._should_connect() is True

    @patch("app.services.vndirect_ws_client.is_market_open")
    def test_should_not_connect_market_closed(self, mock_market):
        mock_market.return_value = False
        client = self._make_client()
        assert client._should_connect() is False


class TestVNDirectWSClientHandleMessage:
    """Test message handling dispatch."""

    @pytest.mark.asyncio
    async def test_handle_sp_message_dispatches(self):
        on_price = AsyncMock()
        client = VNDirectWSClient(
            symbols=["VNM"],
            on_price_update=on_price,
        )
        sp_data = (
            "HOSE|2025-01-15|10:30:00|VNM|Vinamilk|S|1000000|500000"
            "|82000|83000|82500|84000|15000|85000|81000|87500|79500"
            "|83500|125000000000|10000|5000|0|12345"
        )
        import json
        raw_msg = json.dumps({"type": "SP", "data": sp_data})
        await client._handle_message(raw_msg)
        on_price.assert_called_once()
        call_arg = on_price.call_args[0][0]
        assert "VNM" in call_arg
        assert call_arg["VNM"]["price"] == 84000.0

    @pytest.mark.asyncio
    async def test_handle_ba_message_dispatches(self):
        on_price = AsyncMock()
        on_ba = AsyncMock()
        client = VNDirectWSClient(
            symbols=["VNM"],
            on_price_update=on_price,
            on_bid_ask_update=on_ba,
        )
        ba_data = (
            "10:30:00|VNM"
            "|83900|5000|83800|3000|83700|2000"
            "|84100|4000|84200|2500|84300|1500"
            "|500000|84000|1000|84000000|15000|12000"
        )
        import json
        raw_msg = json.dumps({"type": "BA", "data": ba_data})
        await client._handle_message(raw_msg)
        on_ba.assert_called_once()
        call_arg = on_ba.call_args[0][0]
        assert "VNM" in call_arg
        assert len(call_arg["VNM"]["bids"]) == 3

    @pytest.mark.asyncio
    async def test_handle_invalid_json_silently_ignored(self):
        on_price = AsyncMock()
        client = VNDirectWSClient(symbols=["VNM"], on_price_update=on_price)
        await client._handle_message("not json at all")
        on_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_unknown_type_ignored(self):
        on_price = AsyncMock()
        client = VNDirectWSClient(symbols=["VNM"], on_price_update=on_price)
        import json
        raw_msg = json.dumps({"type": "MI", "data": "some|data"})
        await client._handle_message(raw_msg)
        on_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_ba_without_callback_ignored(self):
        on_price = AsyncMock()
        client = VNDirectWSClient(
            symbols=["VNM"],
            on_price_update=on_price,
            on_bid_ask_update=None,
        )
        ba_data = (
            "10:30:00|VNM"
            "|83900|5000|83800|3000|83700|2000"
            "|84100|4000|84200|2500|84300|1500"
            "|500000|84000|1000|84000000|15000|12000"
        )
        import json
        raw_msg = json.dumps({"type": "BA", "data": ba_data})
        await client._handle_message(raw_msg)
        # Should not raise — just silently skip


# ─── _try_float helper ───────────────────────────────────────────────────────


class TestTryFloat:
    def test_valid_float(self):
        assert _try_float("123.45") == 123.45

    def test_valid_int(self):
        assert _try_float("100") == 100.0

    def test_invalid(self):
        assert _try_float("abc") == 0.0

    def test_none(self):
        assert _try_float(None) == 0.0

    def test_empty(self):
        assert _try_float("") == 0.0
