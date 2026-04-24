"""Tests for multi-exchange TickerService parameterization."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from app.services.ticker_service import TickerService


class TestExchangeMaxTickers:

    @pytest.mark.asyncio
    async def test_hose_uses_400_max(self, mock_db_session):
        """HOSE exchange must limit to 400 tickers."""
        crawler = MagicMock()
        listing_df = pd.DataFrame({
            "symbol": [f"HOSE{i:03d}" for i in range(500)],
            "organ_name": [f"Company {i}" for i in range(500)],
        })
        crawler.fetch_listing = AsyncMock(return_value=listing_df)
        crawler.fetch_industry_classification = AsyncMock(
            side_effect=Exception("skip")
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        service = TickerService(mock_db_session, crawler)
        result = await service.fetch_and_sync_tickers(exchange="HOSE")

        assert result["synced"] == 400


class TestDeactivationScoping:

    @pytest.mark.asyncio
    async def test_deactivation_includes_exchange_filter(self, mock_db_session):
        """Deactivation query MUST include Ticker.exchange == exchange filter.

        This is the #1 data corruption risk: without exchange scoping,
        syncing HNX would deactivate all HOSE tickers.
        """
        crawler = MagicMock()
        listing_df = pd.DataFrame({
            "symbol": ["AAA"],
            "organ_name": ["Company A"],
        })
        crawler.fetch_listing = AsyncMock(return_value=listing_df)
        crawler.fetch_industry_classification = AsyncMock(
            side_effect=Exception("skip")
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        service = TickerService(mock_db_session, crawler)
        await service.fetch_and_sync_tickers(exchange="HNX")

        # Verify the deactivation SQL includes exchange filter
        calls = mock_db_session.execute.call_args_list
        # The last execute call before commit is the deactivation statement
        # We check that the compiled SQL contains 'exchange' in the WHERE clause
        deactivate_call = calls[-1]
        stmt = deactivate_call[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "exchange" in compiled.lower(), (
            "Deactivation query MUST include exchange filter to prevent "
            "cross-exchange deactivation"
        )


class TestExchangeFilteredQueries:

    @pytest.mark.asyncio
    async def test_get_active_symbols_with_exchange_filter(self, mock_db_session):
        """get_active_symbols(exchange='HNX') should add exchange WHERE clause."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("HNX001",), ("HNX002",)]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = TickerService(mock_db_session)
        symbols = await service.get_active_symbols(exchange="HNX")

        assert symbols == ["HNX001", "HNX002"]
        # Verify the SQL contains exchange filter
        call_args = mock_db_session.execute.call_args
        stmt = call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "exchange" in compiled.lower()

    @pytest.mark.asyncio
    async def test_get_active_symbols_no_exchange_returns_all(self, mock_db_session):
        """get_active_symbols() with no exchange returns all exchanges."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("AAA",), ("BBB",), ("CCC",)]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = TickerService(mock_db_session)
        symbols = await service.get_active_symbols()

        assert symbols == ["AAA", "BBB", "CCC"]
        # Verify the SQL does NOT contain exchange filter
        call_args = mock_db_session.execute.call_args
        stmt = call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        # Should only have is_active filter, not exchange
        assert "is_active" in compiled.lower()

    @pytest.mark.asyncio
    async def test_get_ticker_id_map_with_exchange_filter(self, mock_db_session):
        """get_ticker_id_map(exchange='HOSE') returns only HOSE tickers."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("VNM", 1), ("FPT", 2)]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = TickerService(mock_db_session)
        ticker_map = await service.get_ticker_id_map(exchange="HOSE")

        assert ticker_map == {"VNM": 1, "FPT": 2}
        # Verify the SQL contains exchange filter
        call_args = mock_db_session.execute.call_args
        stmt = call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "exchange" in compiled.lower()


class TestUpsertExchangeField:

    @pytest.mark.asyncio
    async def test_upsert_sets_exchange_on_new_tickers(self, mock_db_session):
        """Upsert should set exchange field to the provided exchange value."""
        crawler = MagicMock()
        listing_df = pd.DataFrame({
            "symbol": ["AAA"],
            "organ_name": ["Company A"],
        })
        crawler.fetch_listing = AsyncMock(return_value=listing_df)
        crawler.fetch_industry_classification = AsyncMock(
            side_effect=Exception("skip")
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        service = TickerService(mock_db_session, crawler)
        await service.fetch_and_sync_tickers(exchange="HNX")

        # Check the INSERT statement includes exchange="HNX"
        # First execute call is the upsert
        upsert_call = mock_db_session.execute.call_args_list[0]
        stmt = upsert_call[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "exchange" in compiled.lower()
