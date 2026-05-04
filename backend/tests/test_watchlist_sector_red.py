"""RED phase tests for Task 1: sector_group support.

These tests verify the behaviors defined in the plan. They should
FAIL before implementation and PASS after.
"""
import pytest


class TestModelHasSectorGroup:
    """UserWatchlist ORM model must expose sector_group."""

    def test_model_has_sector_group_attribute(self):
        from app.models.user_watchlist import UserWatchlist
        assert hasattr(UserWatchlist, "sector_group"), "sector_group missing from model"


class TestSchemasExist:
    """Pydantic schemas must include sector_group support."""

    def test_watchlist_item_response_has_sector_group(self):
        from app.schemas.watchlist import WatchlistItemResponse
        item = WatchlistItemResponse(symbol="VNM", created_at="2025-01-01T00:00:00")
        assert hasattr(item, "sector_group")
        assert item.sector_group is None  # default

    def test_watchlist_update_request_exists(self):
        from app.schemas.watchlist import WatchlistUpdateRequest
        req = WatchlistUpdateRequest(sector_group="Ngân hàng")
        assert req.sector_group == "Ngân hàng"

    def test_watchlist_add_request_accepts_sector_group(self):
        from app.schemas.watchlist import WatchlistAddRequest
        req = WatchlistAddRequest(symbol="VNM", sector_group="Custom")
        assert req.sector_group == "Custom"

    def test_watchlist_add_request_sector_group_optional(self):
        from app.schemas.watchlist import WatchlistAddRequest
        req = WatchlistAddRequest(symbol="VNM")
        assert req.sector_group is None


class TestEndpointsExist:
    """API endpoints must be importable."""

    def test_patch_endpoint_importable(self):
        from app.api.watchlist import update_watchlist_item
        assert callable(update_watchlist_item)

    def test_sectors_endpoint_importable(self):
        from app.api.tickers import list_sectors
        assert callable(list_sectors)
