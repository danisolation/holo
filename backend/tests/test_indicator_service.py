"""Tests for IndicatorService — ta library computation and storage."""
import pytest
import pandas as pd
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock


class TestComputeIndicators:
    """Test the pure computation function (no DB needed)."""

    def test_returns_12_indicators(self):
        """_compute_indicators must return exactly 12 named indicator Series."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        result = svc._compute_indicators(close)
        expected_keys = {
            "rsi_14", "macd_line", "macd_signal", "macd_histogram",
            "sma_20", "sma_50", "sma_200", "ema_12", "ema_26",
            "bb_upper", "bb_middle", "bb_lower",
        }
        assert set(result.keys()) == expected_keys

    def test_series_length_matches_input(self):
        """Each indicator Series must have same length as input."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(250)])
        result = svc._compute_indicators(close)
        for name, series in result.items():
            assert len(series) == 250, f"{name} has wrong length"

    def test_rsi_warmup_produces_nan(self):
        """RSI(14) must have NaN for first 13 rows (warm-up period)."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(250)])
        result = svc._compute_indicators(close)
        # First 13 rows should be NaN
        assert pd.isna(result["rsi_14"].iloc[0])
        # Row 14+ should have values
        assert not pd.isna(result["rsi_14"].iloc[20])

    def test_sma200_warmup_produces_nan(self):
        """SMA(200) must have NaN for first 199 rows."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(250)])
        result = svc._compute_indicators(close)
        assert pd.isna(result["sma_200"].iloc[198])
        assert not pd.isna(result["sma_200"].iloc[199])


class TestSafeDecimal:
    """Test the NaN→None conversion."""

    def test_normal_float_converts(self):
        from app.services.indicator_service import IndicatorService
        result = IndicatorService._safe_decimal(42.123456)
        assert isinstance(result, Decimal)

    def test_nan_returns_none(self):
        from app.services.indicator_service import IndicatorService
        assert IndicatorService._safe_decimal(float("nan")) is None

    def test_none_returns_none(self):
        from app.services.indicator_service import IndicatorService
        assert IndicatorService._safe_decimal(None) is None


class TestComputeForTicker:
    """Test compute_for_ticker with mocked DB."""

    @pytest.mark.asyncio
    async def test_skips_ticker_with_few_data_points(self):
        """Tickers with < 20 price rows must be skipped."""
        from app.services.indicator_service import IndicatorService
        mock_session = AsyncMock()
        # Return only 10 rows
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(f"2024-01-{i:02d}", 100.0 + i) for i in range(1, 11)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = IndicatorService(mock_session)
        result = await svc.compute_for_ticker(1, "TEST")
        assert result == 0
