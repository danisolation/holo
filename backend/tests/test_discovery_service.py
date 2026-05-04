"""Unit tests for discovery scoring engine.

Tests scoring functions (boundary values, None handling) and
DiscoveryService behavior (batch processing, skip logic).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta

from app.services.discovery_service import (
    DiscoveryService,
    score_rsi,
    score_macd,
    score_adx,
    score_volume,
    score_pe,
    score_roe,
)


class TestScoreRsi:
    """RSI scoring: oversold = high, overbought = low."""

    def test_none_returns_none(self):
        assert score_rsi(None) is None

    def test_oversold_max_score(self):
        assert score_rsi(25.0) == 10.0
        assert score_rsi(30.0) == 10.0

    def test_neutral_mid_score(self):
        assert score_rsi(50.0) == 5.0

    def test_overbought_low_score(self):
        result = score_rsi(80.0)
        assert result is not None
        assert result < 2.0

    def test_extreme_overbought_floor_zero(self):
        result = score_rsi(100.0)
        assert result == 0.0


class TestScoreMacd:
    """MACD histogram scoring: positive = bullish momentum."""

    def test_none_returns_none(self):
        assert score_macd(None) is None

    def test_strong_positive(self):
        assert score_macd(2.0) == 10.0

    def test_zero_neutral(self):
        assert score_macd(0.0) == 5.0

    def test_strong_negative(self):
        assert score_macd(-2.0) == 0.0

    def test_clamped_above_2(self):
        # Values beyond +2 clamped to 10
        assert score_macd(5.0) == 10.0

    def test_clamped_below_neg2(self):
        # Values below -2 clamped to 0
        assert score_macd(-5.0) == 0.0


class TestScoreAdx:
    """ADX scoring: strong uptrend = high, strong downtrend = low."""

    def test_none_returns_none(self):
        assert score_adx(None, None, None) is None

    def test_strong_bullish_trend(self):
        # ADX=50, +DI > -DI → max score
        result = score_adx(50.0, 30.0, 10.0)
        assert result == 10.0

    def test_strong_bearish_trend(self):
        # ADX=50, -DI > +DI → low score (direction_bias=0.3)
        result = score_adx(50.0, 10.0, 30.0)
        assert result == pytest.approx(3.0)

    def test_weak_trend(self):
        # ADX=10, no clear direction
        result = score_adx(10.0, None, None)
        assert result is not None
        assert result < 5.0


class TestScoreVolume:
    """Volume scoring: higher liquidity = better."""

    def test_none_returns_none(self):
        assert score_volume(None) is None

    def test_zero_returns_none(self):
        assert score_volume(0) is None

    def test_high_volume_max(self):
        assert score_volume(1_000_000) == 10.0

    def test_low_volume(self):
        result = score_volume(50_000)
        assert result == pytest.approx(0.5)

    def test_very_high_capped(self):
        # Capped at 10
        assert score_volume(5_000_000) == 10.0


class TestScorePe:
    """P/E scoring: lower = undervalued."""

    def test_none_returns_none(self):
        assert score_pe(None) is None

    def test_negative_pe_zero(self):
        assert score_pe(-5.0) == 0.0

    def test_low_pe_max(self):
        assert score_pe(8.0) == 10.0

    def test_pe_exactly_10(self):
        assert score_pe(10.0) == 10.0

    def test_high_pe_low_score(self):
        result = score_pe(30.0)
        assert result is not None
        assert result < 3.0


class TestScoreRoe:
    """ROE scoring: higher efficiency = better. Input is decimal (0.15 = 15%)."""

    def test_none_returns_none(self):
        assert score_roe(None) is None

    def test_high_roe_max(self):
        assert score_roe(0.25) == 10.0
        assert score_roe(0.20) == 10.0

    def test_medium_roe(self):
        result = score_roe(0.15)
        assert result == 7.0

    def test_low_roe(self):
        result = score_roe(0.05)
        assert result == pytest.approx(2.0)

    def test_very_low_roe(self):
        result = score_roe(0.01)
        assert result is not None
        assert result < 2.0


class TestDiscoveryService:
    """Integration tests for DiscoveryService.score_all_tickers."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_score_all_tickers_returns_expected_keys(self, mock_session):
        """score_all_tickers returns dict with success/failed/skipped/failed_symbols."""
        with patch.object(DiscoveryService, '_cleanup_old_results', return_value=0), \
             patch('app.services.discovery_service.TickerService') as MockTickerSvc, \
             patch.object(DiscoveryService, '_fetch_latest_indicators', return_value={}), \
             patch.object(DiscoveryService, '_fetch_latest_financials', return_value={}), \
             patch.object(DiscoveryService, '_fetch_avg_volumes', return_value={}), \
             patch.object(DiscoveryService, '_bulk_upsert', return_value=None):

            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.get_ticker_id_map.return_value = {"VNM": 1, "FPT": 2}
            MockTickerSvc.return_value = mock_ticker_instance

            service = DiscoveryService(mock_session)
            result = await service.score_all_tickers()

            assert "success" in result
            assert "failed" in result
            assert "skipped" in result
            assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_tickers_with_insufficient_dimensions_skipped(self, mock_session):
        """Tickers with < 2 scoreable dimensions are skipped."""
        with patch.object(DiscoveryService, '_cleanup_old_results', return_value=0), \
             patch('app.services.discovery_service.TickerService') as MockTickerSvc, \
             patch.object(DiscoveryService, '_fetch_latest_indicators', return_value={1: {"rsi_14": None, "macd_histogram": None, "adx_14": None, "plus_di_14": None, "minus_di_14": None}}), \
             patch.object(DiscoveryService, '_fetch_latest_financials', return_value={1: {"pe": None, "roe": None}}), \
             patch.object(DiscoveryService, '_fetch_avg_volumes', return_value={1: None}), \
             patch.object(DiscoveryService, '_bulk_upsert', return_value=None):

            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.get_ticker_id_map.return_value = {"VNM": 1}
            MockTickerSvc.return_value = mock_ticker_instance

            service = DiscoveryService(mock_session)
            result = await service.score_all_tickers()

            assert result["skipped"] == 1
            assert result["success"] == 0

    @pytest.mark.asyncio
    async def test_ticker_with_all_dimensions_scores_successfully(self, mock_session):
        """Ticker with all 6 dimensions available is scored successfully."""
        with patch.object(DiscoveryService, '_cleanup_old_results', return_value=0), \
             patch('app.services.discovery_service.TickerService') as MockTickerSvc, \
             patch.object(DiscoveryService, '_fetch_latest_indicators', return_value={1: {"rsi_14": 40.0, "macd_histogram": 1.0, "adx_14": 30.0, "plus_di_14": 25.0, "minus_di_14": 15.0}}), \
             patch.object(DiscoveryService, '_fetch_latest_financials', return_value={1: {"pe": 12.0, "roe": 0.18}}), \
             patch.object(DiscoveryService, '_fetch_avg_volumes', return_value={1: 500_000}), \
             patch.object(DiscoveryService, '_bulk_upsert', return_value=None):

            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.get_ticker_id_map.return_value = {"VNM": 1}
            MockTickerSvc.return_value = mock_ticker_instance

            service = DiscoveryService(mock_session)
            result = await service.score_all_tickers()

            assert result["success"] == 1
            assert result["skipped"] == 0
            assert result["failed"] == 0

