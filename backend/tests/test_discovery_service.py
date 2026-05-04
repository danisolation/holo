"""Tests for DiscoveryService scoring functions and service logic.

TDD RED phase: These tests define the expected behavior before implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta


# ─── Scoring Function Tests ──────────────────────────────────────────────────

class TestScoreRsi:
    """RSI scoring: oversold (< 30) = high opportunity."""

    def test_none_returns_none(self):
        from app.services.discovery_service import score_rsi
        assert score_rsi(None) is None

    def test_oversold_25_returns_10(self):
        from app.services.discovery_service import score_rsi
        assert score_rsi(25.0) == 10.0

    def test_oversold_30_returns_10(self):
        from app.services.discovery_service import score_rsi
        assert score_rsi(30.0) == 10.0

    def test_neutral_50_returns_5(self):
        from app.services.discovery_service import score_rsi
        assert score_rsi(50.0) == 5.0

    def test_overbought_80_returns_low(self):
        from app.services.discovery_service import score_rsi
        result = score_rsi(80.0)
        assert result is not None
        assert result <= 1.5  # overbought = low score


class TestScoreMacd:
    """MACD histogram score: positive = bullish momentum."""

    def test_none_returns_none(self):
        from app.services.discovery_service import score_macd
        assert score_macd(None) is None

    def test_strong_positive_returns_10(self):
        from app.services.discovery_service import score_macd
        assert score_macd(2.0) == 10.0

    def test_zero_returns_5(self):
        from app.services.discovery_service import score_macd
        assert score_macd(0.0) == 5.0

    def test_strong_negative_returns_0(self):
        from app.services.discovery_service import score_macd
        assert score_macd(-2.0) == 0.0

    def test_extreme_positive_capped_at_10(self):
        from app.services.discovery_service import score_macd
        assert score_macd(5.0) == 10.0  # clamped to 2.0 → 10.0


class TestScoreAdx:
    """ADX score: strong uptrend = high score."""

    def test_none_returns_none(self):
        from app.services.discovery_service import score_adx
        assert score_adx(None, None, None) is None

    def test_strong_bullish_trend(self):
        from app.services.discovery_service import score_adx
        result = score_adx(50.0, 30.0, 10.0)
        assert result is not None
        assert result >= 7.0  # strong ADX + bullish direction

    def test_strong_bearish_trend_gets_low(self):
        from app.services.discovery_service import score_adx
        result = score_adx(50.0, 10.0, 30.0)
        assert result is not None
        assert result <= 4.0  # bearish bias reduces score


class TestScoreVolume:
    """Volume liquidity score: higher volume = better."""

    def test_none_returns_none(self):
        from app.services.discovery_service import score_volume
        assert score_volume(None) is None

    def test_zero_returns_none(self):
        from app.services.discovery_service import score_volume
        assert score_volume(0) is None

    def test_high_volume_1m_returns_10(self):
        from app.services.discovery_service import score_volume
        assert score_volume(1_000_000) == 10.0

    def test_low_volume_50k_returns_0_5(self):
        from app.services.discovery_service import score_volume
        assert score_volume(50_000) == 0.5


class TestScorePe:
    """P/E score: lower P/E = potentially undervalued."""

    def test_none_returns_none(self):
        from app.services.discovery_service import score_pe
        assert score_pe(None) is None

    def test_negative_pe_returns_0(self):
        from app.services.discovery_service import score_pe
        assert score_pe(-5.0) == 0.0

    def test_low_pe_8_returns_10(self):
        from app.services.discovery_service import score_pe
        assert score_pe(8.0) == 10.0

    def test_high_pe_30_returns_low(self):
        from app.services.discovery_service import score_pe
        result = score_pe(30.0)
        assert result is not None
        assert result <= 3.0


class TestScoreRoe:
    """ROE score: higher efficiency = better. ROE stored as decimal (0.15 = 15%)."""

    def test_none_returns_none(self):
        from app.services.discovery_service import score_roe
        assert score_roe(None) is None

    def test_high_roe_25_pct_returns_10(self):
        from app.services.discovery_service import score_roe
        assert score_roe(0.25) == 10.0

    def test_low_roe_5_pct_returns_around_5(self):
        from app.services.discovery_service import score_roe
        result = score_roe(0.05)
        assert result is not None
        assert 2.0 <= result <= 5.0


# ─── Service Tests ───────────────────────────────────────────────────────────

class TestDiscoveryServiceCleanup:
    """Test that _cleanup_old_results deletes old rows."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_old_results(self, mock_db_session):
        from app.services.discovery_service import DiscoveryService
        mock_db_session.execute = AsyncMock(return_value=MagicMock(rowcount=5))
        svc = DiscoveryService(mock_db_session)
        deleted = await svc._cleanup_old_results()
        assert deleted == 5
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()


class TestDiscoveryServiceScoreAll:
    """Test score_all_tickers result structure and skip logic."""

    @pytest.mark.asyncio
    async def test_returns_correct_structure(self, mock_db_session):
        """score_all_tickers returns dict with success, failed, skipped, failed_symbols."""
        from app.services.discovery_service import DiscoveryService

        # Mock all dependencies
        with patch("app.services.discovery_service.TickerService") as MockTickerSvc:
            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.get_ticker_id_map = AsyncMock(return_value={})
            MockTickerSvc.return_value = mock_ticker_instance
            mock_db_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))
            mock_db_session.commit = AsyncMock()

            svc = DiscoveryService(mock_db_session)
            result = await svc.score_all_tickers()

            assert "success" in result
            assert "failed" in result
            assert "skipped" in result
            assert "failed_symbols" in result

    @pytest.mark.asyncio
    async def test_min_dimensions_skip(self, mock_db_session):
        """Tickers with fewer than 2 scoreable dimensions are skipped."""
        from app.services.discovery_service import DiscoveryService

        # Mock ticker with only 1 dimension (RSI only, no financials/volume)
        with patch("app.services.discovery_service.TickerService") as MockTickerSvc:
            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.get_ticker_id_map = AsyncMock(return_value={"VNM": 1})
            MockTickerSvc.return_value = mock_ticker_instance

            # Indicators: only RSI available
            mock_result_ind = MagicMock()
            mock_result_ind.all.return_value = [
                MagicMock(ticker_id=1, rsi_14=50.0, macd_histogram=None, adx_14=None, plus_di_14=None, minus_di_14=None)
            ]
            # Financials: empty
            mock_result_fin = MagicMock()
            mock_result_fin.all.return_value = []
            # Volumes: empty
            mock_result_vol = MagicMock()
            mock_result_vol.all.return_value = []
            # Cleanup returns 0
            mock_result_cleanup = MagicMock(rowcount=0)

            call_count = [0]
            async def side_effect_execute(stmt):
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_result_cleanup
                elif call_count[0] == 2:
                    return mock_result_ind
                elif call_count[0] == 3:
                    return mock_result_fin
                elif call_count[0] == 4:
                    return mock_result_vol
                return MagicMock(rowcount=0)

            mock_db_session.execute = AsyncMock(side_effect=side_effect_execute)
            mock_db_session.commit = AsyncMock()

            svc = DiscoveryService(mock_db_session)
            result = await svc.score_all_tickers()

            assert result["skipped"] == 1
            assert result["success"] == 0
