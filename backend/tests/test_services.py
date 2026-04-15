"""Tests for PriceService and FinancialService."""
import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.services.price_service import PriceService
from app.services.financial_service import FinancialService


class TestPriceService:

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_crawler(self):
        crawler = AsyncMock()
        return crawler

    @pytest.fixture
    def service(self, mock_session, mock_crawler):
        svc = PriceService(mock_session, mock_crawler)
        svc.ticker_service = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_crawl_batch_processes_all_tickers(self, service, mock_crawler):
        """Batch crawl processes each ticker and handles failures."""
        mock_df = pd.DataFrame({
            "time": pd.to_datetime(["2025-01-15"]),
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000000],
        })
        mock_crawler.fetch_ohlcv = AsyncMock(return_value=mock_df)

        ticker_map = {"VNM": 1, "FPT": 2}
        result = await service._crawl_batch(
            ["VNM", "FPT"], ticker_map, "2025-01-01", "2025-01-15"
        )
        assert result["success"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_crawl_batch_skips_empty_data(self, service, mock_crawler):
        """Empty DataFrame from vnstock is handled as skip, not failure."""
        mock_crawler.fetch_ohlcv = AsyncMock(return_value=pd.DataFrame())

        result = await service._crawl_batch(
            ["VNM"], {"VNM": 1}, "2025-01-01", "2025-01-15"
        )
        assert result["skipped"] == 1
        assert result["success"] == 0

    @pytest.mark.asyncio
    async def test_crawl_batch_continues_on_failure(self, service, mock_crawler):
        """Failed tickers are logged and skipped — batch continues."""
        mock_crawler.fetch_ohlcv = AsyncMock(
            side_effect=[Exception("API error"), pd.DataFrame({
                "time": pd.to_datetime(["2025-01-15"]),
                "open": [50.0], "high": [55.0], "low": [49.0],
                "close": [53.0], "volume": [500000],
            })]
        )

        result = await service._crawl_batch(
            ["BAD", "FPT"], {"BAD": 1, "FPT": 2}, "2025-01-01", "2025-01-15"
        )
        assert result["failed"] == 1
        assert result["success"] == 1
        assert "BAD" in result["failed_symbols"]


class TestFinancialService:

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        svc = FinancialService(mock_session, AsyncMock())
        svc.ticker_service = AsyncMock()
        return svc

    def test_safe_decimal_valid(self):
        assert FinancialService._safe_decimal(15.5) == Decimal("15.5")
        assert FinancialService._safe_decimal("3.14") == Decimal("3.14")
        assert FinancialService._safe_decimal(0) == Decimal("0")

    def test_safe_decimal_none_and_nan(self):
        assert FinancialService._safe_decimal(None) is None
        assert FinancialService._safe_decimal(float("nan")) is None

    def test_safe_int_valid(self):
        assert FinancialService._safe_int(2025) == 2025
        assert FinancialService._safe_int(1.0) == 1

    def test_safe_int_none(self):
        assert FinancialService._safe_int(None) is None
        assert FinancialService._safe_int(float("nan")) is None
