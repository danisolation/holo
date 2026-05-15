"""Unit tests for MarketBreadthService.

Tests A/D line, MA breadth, and 52-week highs/lows computation
using mocked DB sessions returning controlled price/indicator data.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.market_breadth_service import MarketBreadthService


# ─── Helper: build mock row objects ──────────────────────────────────────────

def _price_row(ticker_id: int, dt: date, close: float):
    """Create a mock DailyPrice row (ticker_id, date, close, high, low)."""
    row = MagicMock()
    row.ticker_id = ticker_id
    row.date = dt
    row.close = Decimal(str(close))
    row.high = Decimal(str(close + 0.5))
    row.low = Decimal(str(close - 0.5))
    return row


def _indicator_row(ticker_id: int, dt: date, close: float, sma_50: float | None, sma_200: float | None):
    """Create a mock joined DailyPrice+TechnicalIndicator row."""
    row = MagicMock()
    row.ticker_id = ticker_id
    row.date = dt
    row.close = Decimal(str(close))
    row.sma_50 = Decimal(str(sma_50)) if sma_50 is not None else None
    row.sma_200 = Decimal(str(sma_200)) if sma_200 is not None else None
    return row


# ─── A/D Line Tests ─────────────────────────────────────────────────────────

class TestADLineComputation:
    """Test advancing/declining counting logic."""

    @pytest.mark.asyncio
    async def test_basic_ad_line(self, mock_db_session):
        """3 tickers across 3 dates — verify advancing/declining/unchanged counts."""
        d1 = date(2025, 1, 2)
        d2 = date(2025, 1, 3)
        d3 = date(2025, 1, 6)

        # Ticker 1: 10 -> 11 -> 10 (up, down)
        # Ticker 2: 20 -> 20 -> 21 (unchanged, up)
        # Ticker 3: 30 -> 29 -> 28 (down, down)
        price_rows = [
            _price_row(1, d1, 10.0), _price_row(1, d2, 11.0), _price_row(1, d3, 10.0),
            _price_row(2, d1, 20.0), _price_row(2, d2, 20.0), _price_row(2, d3, 21.0),
            _price_row(3, d1, 30.0), _price_row(3, d2, 29.0), _price_row(3, d3, 28.0),
        ]

        # Mock ticker_id_map
        ticker_map = {"AAA": 1, "BBB": 2, "CCC": 3}

        mock_result = MagicMock()
        mock_result.fetchall.return_value = price_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_ad_line(d2, d3)

        # d2: ticker1 up, ticker2 unchanged, ticker3 down => adv=1, dec=1, unch=1
        # d3: ticker1 down, ticker2 up, ticker3 down => adv=1, dec=2, unch=0
        assert len(result) == 2
        day2 = next(r for r in result if r["date"] == d2.isoformat())
        assert day2["advancing"] == 1
        assert day2["declining"] == 1
        assert day2["unchanged"] == 1
        assert day2["net"] == 0

        day3 = next(r for r in result if r["date"] == d3.isoformat())
        assert day3["advancing"] == 1
        assert day3["declining"] == 2
        assert day3["net"] == -1

    @pytest.mark.asyncio
    async def test_all_advancing(self, mock_db_session):
        """All tickers go up — all advancing."""
        d1 = date(2025, 1, 2)
        d2 = date(2025, 1, 3)

        price_rows = [
            _price_row(1, d1, 10.0), _price_row(1, d2, 12.0),
            _price_row(2, d1, 20.0), _price_row(2, d2, 25.0),
        ]
        ticker_map = {"AAA": 1, "BBB": 2}

        mock_result = MagicMock()
        mock_result.fetchall.return_value = price_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_ad_line(d2, d2)

        assert len(result) == 1
        assert result[0]["advancing"] == 2
        assert result[0]["declining"] == 0
        assert result[0]["net"] == 2


# ─── MA Breadth Tests ───────────────────────────────────────────────────────

class TestMABreadthComputation:
    """Test % above MA50/MA200 calculation."""

    @pytest.mark.asyncio
    async def test_basic_ma_breadth(self, mock_db_session):
        """3 tickers: verify above/below MA counting."""
        d1 = date(2025, 1, 3)
        # Ticker 1: close=11, sma50=10, sma200=12 => above_ma50, below_ma200
        # Ticker 2: close=20, sma50=19, sma200=18 => above both
        # Ticker 3: close=28, sma50=30, sma200=25 => below_ma50, above_ma200
        indicator_rows = [
            _indicator_row(1, d1, 11.0, 10.0, 12.0),
            _indicator_row(2, d1, 20.0, 19.0, 18.0),
            _indicator_row(3, d1, 28.0, 30.0, 25.0),
        ]
        ticker_map = {"AAA": 1, "BBB": 2, "CCC": 3}

        mock_result = MagicMock()
        mock_result.fetchall.return_value = indicator_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_ma_breadth(d1, d1)

        assert len(result) == 1
        day = result[0]
        assert day["total_tickers"] == 3
        assert day["above_ma50"] == 2  # tickers 1, 2
        assert day["above_ma200"] == 2  # tickers 2, 3
        assert day["pct_above_ma50"] == pytest.approx(66.7, abs=0.1)
        assert day["pct_above_ma200"] == pytest.approx(66.7, abs=0.1)

    @pytest.mark.asyncio
    async def test_null_sma_excluded(self, mock_db_session):
        """Tickers with NULL sma are excluded from that metric's count."""
        d1 = date(2025, 1, 3)
        # Ticker 1: close=11, sma50=10, sma200=None => counted for ma50 only
        # Ticker 2: close=20, sma50=19, sma200=18 => counted for both
        indicator_rows = [
            _indicator_row(1, d1, 11.0, 10.0, None),
            _indicator_row(2, d1, 20.0, 19.0, 18.0),
        ]
        ticker_map = {"AAA": 1, "BBB": 2}

        mock_result = MagicMock()
        mock_result.fetchall.return_value = indicator_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_ma_breadth(d1, d1)

        assert len(result) == 1
        day = result[0]
        assert day["above_ma50"] == 2  # both above
        assert day["total_tickers"] == 2
        # For pct_above_ma200: only 1 ticker has non-null sma200, and it's above
        assert day["above_ma200"] == 1


# ─── 52-Week Highs/Lows Tests ───────────────────────────────────────────────

class TestHighsLowsComputation:
    """Test new 52-week high/low detection."""

    @pytest.mark.asyncio
    async def test_basic_highs_lows(self, mock_db_session):
        """Ticker hitting new high on last day."""
        base = date(2024, 1, 1)
        # 260 trading days of data for 1 ticker
        # Prices: 10.0 for first 259 days, then 11.0 on last day (new high)
        price_rows = []
        for i in range(260):
            dt = base + timedelta(days=i)
            close = 10.0 if i < 259 else 11.0
            price_rows.append(_price_row(1, dt, close))

        ticker_map = {"AAA": 1}
        target_date = price_rows[-1].date

        mock_result = MagicMock()
        mock_result.fetchall.return_value = price_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_highs_lows(target_date, target_date)

        assert len(result) >= 1
        day = next(r for r in result if r["date"] == target_date.isoformat())
        assert day["new_highs"] == 1
        assert day["new_lows"] == 0

    @pytest.mark.asyncio
    async def test_new_low(self, mock_db_session):
        """Ticker hitting new low on last day."""
        base = date(2024, 1, 1)
        # Prices: 10.0 for first 259 days, then 9.0 on last day (new low)
        price_rows = []
        for i in range(260):
            dt = base + timedelta(days=i)
            close = 10.0 if i < 259 else 9.0
            price_rows.append(_price_row(1, dt, close))

        ticker_map = {"AAA": 1}
        target_date = price_rows[-1].date

        mock_result = MagicMock()
        mock_result.fetchall.return_value = price_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_highs_lows(target_date, target_date)

        assert len(result) >= 1
        day = next(r for r in result if r["date"] == target_date.isoformat())
        assert day["new_highs"] == 0
        assert day["new_lows"] == 1


# ─── Edge Cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge case handling."""

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_db_session):
        """No price data returns empty lists."""
        ticker_map = {}  # no tickers

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_all_breadth(date(2025, 1, 1), date(2025, 1, 31))

        assert result["ad_line"] == []
        assert result["ma_breadth"] == []
        assert result["highs_lows"] == []

    @pytest.mark.asyncio
    async def test_single_ticker_ad(self, mock_db_session):
        """Single ticker A/D line."""
        d1 = date(2025, 1, 2)
        d2 = date(2025, 1, 3)
        price_rows = [
            _price_row(1, d1, 10.0),
            _price_row(1, d2, 11.0),
        ]
        ticker_map = {"AAA": 1}

        mock_result = MagicMock()
        mock_result.fetchall.return_value = price_rows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.market_breadth_service.TickerService") as MockTS:
            ts_instance = AsyncMock()
            ts_instance.get_ticker_id_map = AsyncMock(return_value=ticker_map)
            MockTS.return_value = ts_instance

            service = MarketBreadthService(mock_db_session)
            result = await service.get_ad_line(d2, d2)

        assert len(result) == 1
        assert result[0]["advancing"] == 1
        assert result[0]["declining"] == 0
