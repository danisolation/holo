"""Tests for IndicatorService — ta library computation and storage."""
import pytest
import pandas as pd
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock


class TestComputeIndicators:
    """Test the pure computation function (no DB needed)."""

    def test_returns_18_indicators(self):
        """_compute_indicators must return exactly 18 named indicator Series."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        expected_keys = {
            "rsi_14", "macd_line", "macd_signal", "macd_histogram",
            "sma_20", "sma_50", "sma_200", "ema_12", "ema_26",
            "bb_upper", "bb_middle", "bb_lower",
            "atr_14", "adx_14", "plus_di_14", "minus_di_14",
            "stoch_k_14", "stoch_d_14",
        }
        assert set(result.keys()) == expected_keys

    def test_series_length_matches_input(self):
        """Each indicator Series must have same length as input."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(250)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        for name, series in result.items():
            assert len(series) == 250, f"{name} has wrong length"

    def test_rsi_warmup_produces_nan(self):
        """RSI(14) must have NaN for first 13 rows (warm-up period)."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(250)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        # First 13 rows should be NaN
        assert pd.isna(result["rsi_14"].iloc[0])
        # Row 14+ should have values
        assert not pd.isna(result["rsi_14"].iloc[20])

    def test_sma200_warmup_produces_nan(self):
        """SMA(200) must have NaN for first 199 rows."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(250)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        assert pd.isna(result["sma_200"].iloc[198])
        assert not pd.isna(result["sma_200"].iloc[199])

    def test_atr_warmup_is_nan(self):
        """ATR warm-up must be NaN (not 0.0) for first 13 rows."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        # First 13 rows should be NaN (warm-up), NOT 0.0
        assert pd.isna(result["atr_14"].iloc[0]), "ATR warm-up row 0 should be NaN"
        assert pd.isna(result["atr_14"].iloc[12]), "ATR warm-up row 12 should be NaN"
        # Row 14+ should have actual values
        assert not pd.isna(result["atr_14"].iloc[20]), "ATR row 20 should have a value"
        assert result["atr_14"].iloc[20] > 0, "ATR must be positive"

    def test_adx_warmup_is_nan(self):
        """ADX warm-up must be NaN for first 27 rows; +DI/-DI NaN for first 15."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        assert pd.isna(result["adx_14"].iloc[0]), "ADX warm-up row 0 should be NaN"
        assert pd.isna(result["adx_14"].iloc[26]), "ADX warm-up row 26 should be NaN"
        assert not pd.isna(result["adx_14"].iloc[40]), "ADX row 40 should have a value"
        # +DI/-DI have shorter warm-up (~15 rows)
        assert pd.isna(result["plus_di_14"].iloc[0]), "+DI warm-up row 0 should be NaN"
        assert not pd.isna(result["plus_di_14"].iloc[20]), "+DI row 20 should have a value"

    def test_stochastic_series_valid(self):
        """Stochastic %K has NaN for first 13 rows, %D for first 15."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        assert pd.isna(result["stoch_k_14"].iloc[0]), "%K warm-up row 0 should be NaN"
        assert not pd.isna(result["stoch_k_14"].iloc[20]), "%K row 20 should have a value"
        # %K values should be between 0 and 100
        valid_k = result["stoch_k_14"].dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all(), "%K must be in [0, 100]"
        assert pd.isna(result["stoch_d_14"].iloc[0]), "%D warm-up row 0 should be NaN"
        assert not pd.isna(result["stoch_d_14"].iloc[20]), "%D row 20 should have a value"

    def test_compute_indicators_requires_high_low(self):
        """_compute_indicators must accept close, high, low parameters."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        assert isinstance(result, dict)
        assert len(result) == 18


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


class TestIndicatorResponseSchema:
    """Test that IndicatorResponse schema has new fields."""

    def test_indicator_response_has_new_fields(self):
        from app.schemas.analysis import IndicatorResponse
        fields = IndicatorResponse.model_fields
        new_fields = ["atr_14", "adx_14", "plus_di_14", "minus_di_14", "stoch_k_14", "stoch_d_14"]
        for field in new_fields:
            assert field in fields, f"IndicatorResponse missing field: {field}"
            assert fields[field].annotation == (float | None), f"{field} should be float | None"
