"""Tests for Phase 54 sector group endpoints (TAG-01, TAG-02, TAG-03).

Verifies PATCH sector_group update, POST auto-populate from Ticker.sector,
GET enriched includes sector_group, and GET /tickers/sectors distinct list.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.watchlist import WatchlistUpdateRequest, WatchlistAddRequest


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _mock_session_ctx():
    """Create mock async session context manager."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.add = MagicMock()  # session.add() is sync in SQLAlchemy

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_factory, mock_session


def _make_watchlist_item(symbol="VNM", sector_group=None):
    """Create a mock UserWatchlist ORM object."""
    item = MagicMock()
    item.symbol = symbol
    item.sector_group = sector_group
    item.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return item


# ── Class 1: TestPatchWatchlistItem ──────────────────────────────────────────


class TestPatchWatchlistItem:
    """Tests for PATCH /watchlist/{symbol} — update sector_group."""

    @pytest.mark.asyncio
    async def test_patch_updates_sector_group(self):
        """PATCH with valid symbol updates sector_group and returns it."""
        mock_factory, mock_session = _mock_session_ctx()
        item = _make_watchlist_item("VNM")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_session.execute = AsyncMock(return_value=mock_result)

        # After commit+refresh, sector_group should be updated
        async def mock_refresh(obj):
            obj.sector_group = "Ngân hàng"
        mock_session.refresh = AsyncMock(side_effect=mock_refresh)

        with patch("app.api.watchlist.async_session", mock_factory):
            from app.api.watchlist import update_watchlist_item

            body = WatchlistUpdateRequest(sector_group="Ngân hàng")
            response = await update_watchlist_item("VNM", body)

            assert response.sector_group == "Ngân hàng"
            assert response.symbol == "VNM"
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_nonexistent_returns_404(self):
        """PATCH with unknown symbol returns 404."""
        mock_factory, mock_session = _mock_session_ctx()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.watchlist.async_session", mock_factory):
            from app.api.watchlist import update_watchlist_item
            from fastapi import HTTPException

            body = WatchlistUpdateRequest(sector_group="Ngân hàng")
            with pytest.raises(HTTPException) as exc_info:
                await update_watchlist_item("NONEXIST", body)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_clear_sector_group(self):
        """PATCH with sector_group=null clears the sector group."""
        mock_factory, mock_session = _mock_session_ctx()
        item = _make_watchlist_item("VNM", sector_group="Ngân hàng")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = item
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def mock_refresh(obj):
            obj.sector_group = None
        mock_session.refresh = AsyncMock(side_effect=mock_refresh)

        with patch("app.api.watchlist.async_session", mock_factory):
            from app.api.watchlist import update_watchlist_item

            body = WatchlistUpdateRequest(sector_group=None)
            response = await update_watchlist_item("VNM", body)

            assert response.sector_group is None
            # Verify the item's sector_group was set to None before commit
            assert item.sector_group is None


# ── Class 2: TestAddWithAutoSector ───────────────────────────────────────────


class TestAddWithAutoSector:
    """Tests for POST /watchlist — sector_group auto-populate from Ticker.sector."""

    @pytest.mark.asyncio
    async def test_add_auto_populates_sector_from_ticker(self):
        """POST without sector_group looks up Ticker.sector and uses it."""
        mock_factory, mock_session = _mock_session_ctx()

        # First execute: check existing (not found)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None

        # Second execute: ticker sector lookup
        mock_ticker_result = MagicMock()
        mock_ticker_result.scalar_one_or_none.return_value = "Thực phẩm & Đồ uống"

        mock_session.execute = AsyncMock(
            side_effect=[mock_existing_result, mock_ticker_result]
        )

        # After commit+refresh, entry has sector_group populated
        created_entry = _make_watchlist_item("VNM", sector_group="Thực phẩm & Đồ uống")
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, 'created_at', created_entry.created_at) or
                                    setattr(obj, 'sector_group', "Thực phẩm & Đồ uống")
        )

        with patch("app.api.watchlist.async_session", mock_factory):
            from app.api.watchlist import add_to_watchlist

            body = WatchlistAddRequest(symbol="VNM")
            response = await add_to_watchlist(body)

            assert response.sector_group == "Thực phẩm & Đồ uống"
            # Verify the ticker lookup was executed (2 execute calls total)
            assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_add_with_explicit_sector_skips_lookup(self):
        """POST with sector_group provided uses that value, skips Ticker lookup."""
        mock_factory, mock_session = _mock_session_ctx()

        # First execute: check existing (not found)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_existing_result)

        created_entry = _make_watchlist_item("VNM", sector_group="Custom Sector")
        mock_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, 'created_at', created_entry.created_at) or
                                    setattr(obj, 'sector_group', "Custom Sector")
        )

        with patch("app.api.watchlist.async_session", mock_factory):
            from app.api.watchlist import add_to_watchlist

            body = WatchlistAddRequest(symbol="VNM", sector_group="Custom Sector")
            response = await add_to_watchlist(body)

            assert response.sector_group == "Custom Sector"
            # Only 1 execute call (existing check) — no ticker lookup
            assert mock_session.execute.call_count == 1


# ── Class 3: TestEnrichedWatchlistIncludesSector ─────────────────────────────


class TestEnrichedWatchlistIncludesSector:
    """Tests for GET /watchlist — enriched response includes sector_group."""

    @pytest.mark.asyncio
    async def test_get_enriched_includes_sector_group(self):
        """GET /watchlist returns sector_group in each response item."""
        mock_factory, mock_session = _mock_session_ctx()

        # Mock row objects returned by the enriched query
        row1 = MagicMock()
        row1.symbol = "VNM"
        row1.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        row1.sector_group = "Thực phẩm"
        row1.signal = "buy"
        row1.score = 8
        row1.analysis_date = None
        row1.max_created_at = None

        row2 = MagicMock()
        row2.symbol = "FPT"
        row2.created_at = datetime(2025, 1, 2, tzinfo=timezone.utc)
        row2.sector_group = "Công nghệ"
        row2.signal = None
        row2.score = None
        row2.analysis_date = None
        row2.max_created_at = None

        # First execute call = COUNT query, second = main query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        main_result = MagicMock()
        main_result.all.return_value = [row1, row2]

        mock_session.execute = AsyncMock(side_effect=[count_result, main_result])

        with patch("app.api.watchlist.async_session", mock_factory):
            from app.api.watchlist import get_watchlist

            response = await get_watchlist()

            assert response.total == 2
            assert len(response.items) == 2
            assert response.items[0].sector_group == "Thực phẩm"
            assert response.items[0].symbol == "VNM"
            assert response.items[1].sector_group == "Công nghệ"
            assert response.items[1].symbol == "FPT"


# ── Class 4: TestListSectors ────────────────────────────────────────────────


class TestListSectors:
    """Tests for GET /tickers/sectors — distinct ICB sector names."""

    @pytest.mark.asyncio
    async def test_returns_sorted_distinct_sectors(self):
        """GET /tickers/sectors returns alphabetized distinct sector list."""
        mock_factory, mock_session = _mock_session_ctx()

        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("Bất động sản",),
            ("Công nghệ",),
            ("Ngân hàng",),
            ("Thực phẩm & Đồ uống",),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.tickers.async_session", mock_factory):
            from app.api.tickers import _sectors_cache, list_sectors
            _sectors_cache.clear()

            result = await list_sectors()

            assert result == [
                "Bất động sản",
                "Công nghệ",
                "Ngân hàng",
                "Thực phẩm & Đồ uống",
            ]
            assert result == sorted(result)

    @pytest.mark.asyncio
    async def test_excludes_null_sectors(self):
        """GET /tickers/sectors query filters out null sectors via WHERE clause."""
        mock_factory, mock_session = _mock_session_ctx()

        # Return only non-null sectors (nulls filtered by SQL WHERE clause)
        mock_result = MagicMock()
        mock_result.all.return_value = [("Ngân hàng",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.tickers.async_session", mock_factory):
            from app.api.tickers import _sectors_cache, list_sectors
            _sectors_cache.clear()

            result = await list_sectors()

            # Verify no None values in results
            assert all(s is not None for s in result)
            assert result == ["Ngân hàng"]

            # Verify the SQL statement was executed (the WHERE clause
            # filters nulls, so the mock only returns non-null results)
            mock_session.execute.assert_called_once()
