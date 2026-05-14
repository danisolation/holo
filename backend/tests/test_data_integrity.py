"""Tests for data integrity service.

Verifies DataIntegrityService check methods return correct structures
and detect data quality issues using mocked DB sessions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date


class TestDataIntegrityService:
    """Test DataIntegrityService check methods."""

    @pytest.mark.asyncio
    async def test_check_all_returns_structure(self):
        """check_all returns dict with status, total_issues, and 3 check results."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.services.data_integrity_service import DataIntegrityService
        svc = DataIntegrityService(mock_session)
        result = await svc.check_all()

        assert "status" in result
        assert "total_issues" in result
        assert "price_gaps" in result
        assert "duplicates" in result
        assert "stale_analysis" in result

    @pytest.mark.asyncio
    async def test_healthy_when_no_issues(self):
        """Status is 'healthy' when all checks return empty lists."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.services.data_integrity_service import DataIntegrityService
        svc = DataIntegrityService(mock_session)
        result = await svc.check_all()

        assert result["status"] == "healthy"
        assert result["total_issues"] == 0

    @pytest.mark.asyncio
    async def test_check_duplicates_detects_dupes(self):
        """check_duplicates returns entries when count > 1."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("VNM", date(2024, 5, 10), 2)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.services.data_integrity_service import DataIntegrityService
        svc = DataIntegrityService(mock_session)
        result = await svc.check_duplicates()

        assert len(result) == 1
        assert result[0]["ticker_symbol"] == "VNM"
        assert result[0]["count"] == 2
        assert result[0]["date"] == "2024-05-10"

    @pytest.mark.asyncio
    async def test_check_price_gaps_returns_empty_for_no_watchlist(self):
        """check_price_gaps returns [] when watchlist is empty."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.services.data_integrity_service import DataIntegrityService
        svc = DataIntegrityService(mock_session)
        result = await svc.check_price_gaps()

        assert result == []

    @pytest.mark.asyncio
    async def test_check_stale_analysis_returns_stale_tickers(self):
        """check_stale_analysis returns tickers with old analysis."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("FPT", date(2024, 1, 1))]
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.services.data_integrity_service import DataIntegrityService
        svc = DataIntegrityService(mock_session)
        result = await svc.check_stale_analysis()

        assert len(result) == 1
        assert result[0]["ticker_symbol"] == "FPT"
        assert result[0]["last_analysis"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_issues_found_status_when_duplicates_exist(self):
        """Status is 'issues_found' when any check returns results."""
        mock_session = AsyncMock()
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # check_price_gaps: empty watchlist
                result.all.return_value = []
            elif call_count == 2:
                # check_duplicates: one dupe found
                result.all.return_value = [("VNM", date(2024, 5, 10), 2)]
            else:
                # check_stale_analysis: empty
                result.all.return_value = []
            return result

        mock_session.execute = mock_execute

        from app.services.data_integrity_service import DataIntegrityService
        svc = DataIntegrityService(mock_session)
        result = await svc.check_all()

        assert result["status"] == "issues_found"
        assert result["total_issues"] == 1
