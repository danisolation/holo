"""Tests for IndicatorService — ta library computation and storage."""
import pytest
import pandas as pd
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock


class TestComputeIndicators:
    """Test the pure computation function (no DB needed)."""

    def test_returns_27_indicators(self):
        """_compute_indicators must return exactly 27 named indicator Series."""
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
            # Phase 18: Support & Resistance
            "pivot_point", "support_1", "support_2",
            "resistance_1", "resistance_2",
            "fib_236", "fib_382", "fib_500", "fib_618",
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
        assert len(result) == 27

    def test_pivot_point_uses_previous_day(self):
        """Pivot point at index 1 uses previous day's H/L/C; index 0 is NaN."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([100.0 + i * 10.0 for i in range(300)])
        high = close + 5.0
        low = close - 5.0
        result = svc._compute_indicators(close, high, low)
        # Index 0: no prior day → NaN
        assert pd.isna(result["pivot_point"].iloc[0])
        # Index 1: PP = (high[0] + low[0] + close[0]) / 3 = (105 + 95 + 100) / 3 = 100.0
        assert result["pivot_point"].iloc[1] == pytest.approx(100.0)

    def test_pivot_support_resistance_formulas(self):
        """Classic pivot S1/R1/S2/R2 formulas verified at index 1."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([100.0 + i * 10.0 for i in range(300)])
        high = close + 5.0
        low = close - 5.0
        result = svc._compute_indicators(close, high, low)
        # At index 1: prev_high=105, prev_low=95, prev_close=100
        # PP = (105+95+100)/3 = 100.0
        # S1 = 2*PP - prev_high = 200 - 105 = 95.0
        # R1 = 2*PP - prev_low  = 200 - 95  = 105.0
        # S2 = PP - (prev_high - prev_low) = 100 - 10 = 90.0
        # R2 = PP + (prev_high - prev_low) = 100 + 10 = 110.0
        assert result["support_1"].iloc[1] == pytest.approx(95.0)
        assert result["resistance_1"].iloc[1] == pytest.approx(105.0)
        assert result["support_2"].iloc[1] == pytest.approx(90.0)
        assert result["resistance_2"].iloc[1] == pytest.approx(110.0)

    def test_fibonacci_20day_warmup(self):
        """Fibonacci levels are NaN for first 19 rows (rolling(20) needs 19 prior)."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        # Index 18 (19th row): only 19 data points → NaN
        assert pd.isna(result["fib_236"].iloc[18])
        # Index 19 (20th row): rolling(20) has exactly 20 values → should have value
        assert not pd.isna(result["fib_236"].iloc[19])

    def test_fibonacci_level_ordering(self):
        """For non-NaN rows, fib_236 < fib_382 < fib_500 < fib_618."""
        from app.services.indicator_service import IndicatorService
        svc = IndicatorService.__new__(IndicatorService)
        close = pd.Series([float(i + 10) for i in range(300)])
        high = close + 2.0
        low = close - 2.0
        result = svc._compute_indicators(close, high, low)
        # Check at row 19+ where Fibonacci levels exist
        for idx in [19, 50, 100, 200]:
            f236 = result["fib_236"].iloc[idx]
            f382 = result["fib_382"].iloc[idx]
            f500 = result["fib_500"].iloc[idx]
            f618 = result["fib_618"].iloc[idx]
            assert f236 < f382 < f500 < f618, f"Fibonacci ordering violated at index {idx}"


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
        mock_result.fetchall.return_value = [(f"2024-01-{i:02d}", 100.0 + i, 105.0 + i, 95.0 + i) for i in range(1, 11)]
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
