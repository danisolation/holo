"""Tests for VnstockCrawler async wrapper."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from app.crawlers.vnstock_crawler import VnstockCrawler


@pytest.fixture
def crawler():
    return VnstockCrawler(source="VCI")


class TestVnstockCrawler:
    """Verify vnstock calls are properly wrapped in asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_fetch_listing_uses_to_thread(self, crawler):
        """fetch_listing must use asyncio.to_thread, not call vnstock directly."""
        mock_df = pd.DataFrame({
            "symbol": ["VNM", "FPT", "VIC"],
            "exchange": ["HOSE", "HOSE", "HOSE"],
            "type": ["STOCK", "STOCK", "STOCK"],
            "organ_name": ["Vinamilk", "FPT Corp", "Vingroup"],
        })

        with patch("app.crawlers.vnstock_crawler.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_df
            result = await crawler.fetch_listing()
            mock_to_thread.assert_called_once()
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_uses_to_thread(self, crawler):
        """fetch_ohlcv must use asyncio.to_thread."""
        mock_df = pd.DataFrame({
            "time": pd.to_datetime(["2025-01-01"]),
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000000],
        })

        with patch("app.crawlers.vnstock_crawler.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_df
            result = await crawler.fetch_ohlcv("VNM", "2025-01-01", "2025-01-02")
            mock_to_thread.assert_called_once()
            assert "close" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_financial_ratios_uses_to_thread(self, crawler):
        """fetch_financial_ratios must use asyncio.to_thread."""
        mock_df = pd.DataFrame({"pe": [15.0], "pb": [3.0]})

        with patch("app.crawlers.vnstock_crawler.asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_df
            result = await crawler.fetch_financial_ratios("VNM")
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawler_source_default(self):
        """Crawler uses config default source when none specified."""
        crawler = VnstockCrawler()
        # Source comes from settings.vnstock_source (default "VCI")
        assert crawler.source is not None
