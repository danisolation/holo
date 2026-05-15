"""Unit tests for SectorAnalysisService.

Tests cover:
- get_sector_performance returns correct structure with avg changes
- Null/empty sector mapped to "Khác"
- get_sector_flow returns net_volume with correct sign
- Empty result for future date range
- Single-ticker sector works correctly
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_perf_row(sector, ticker_count, avg_today, avg_7d, avg_30d):
    """Helper to create a mock row for sector performance."""
    row = MagicMock()
    row.sector = sector
    row.ticker_count = ticker_count
    row.avg_change_today = avg_today
    row.avg_change_7d = avg_7d
    row.avg_change_30d = avg_30d
    return row


def _make_flow_row(sector, dt, net_vol, buy_vol, sell_vol):
    """Helper to create a mock row for sector flow."""
    row = MagicMock()
    row.sector = sector
    row.date = dt
    row.net_volume = net_vol
    row.buy_volume = buy_vol
    row.sell_volume = sell_vol
    return row


@pytest.mark.asyncio
async def test_get_sector_performance_returns_correct_structure(mock_db_session):
    """Sector performance returns list of dicts with expected keys."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        _make_perf_row("Ngân hàng", 10, 1.5, 3.2, -0.8),
        _make_perf_row("Bất động sản", 5, -0.3, 1.1, 2.5),
    ]
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_performance(
        date(2025, 5, 1), date(2025, 5, 14)
    )

    assert len(result) == 2
    item = result[0]
    assert "sector" in item
    assert "ticker_count" in item
    assert "avg_change_today" in item
    assert "avg_change_7d" in item
    assert "avg_change_30d" in item
    assert item["sector"] == "Ngân hàng"
    assert item["ticker_count"] == 10
    assert item["avg_change_today"] == 1.5


@pytest.mark.asyncio
async def test_get_sector_performance_null_sector_grouped_as_khac(mock_db_session):
    """Tickers with null/empty sector are grouped as 'Khác'."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    # SQL COALESCE already maps null to 'Khác' — verify service passes it through
    mock_result.fetchall.return_value = [
        _make_perf_row("Khác", 3, 0.5, -1.0, 0.0),
    ]
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_performance(
        date(2025, 5, 1), date(2025, 5, 14)
    )

    assert len(result) == 1
    assert result[0]["sector"] == "Khác"
    assert result[0]["ticker_count"] == 3


@pytest.mark.asyncio
async def test_get_sector_performance_empty_result(mock_db_session):
    """Empty date range returns empty list."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_performance(
        date(2099, 1, 1), date(2099, 12, 31)
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_sector_flow_returns_correct_structure(mock_db_session):
    """Sector flow returns list of dicts with net_volume, buy_volume, sell_volume."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        _make_flow_row("Ngân hàng", date(2025, 5, 13), 1500000.0, 2000000.0, 500000.0),
        _make_flow_row("Ngân hàng", date(2025, 5, 14), -300000.0, 400000.0, 700000.0),
    ]
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_flow(
        date(2025, 5, 13), date(2025, 5, 14)
    )

    assert len(result) == 2
    item = result[0]
    assert item["sector"] == "Ngân hàng"
    assert item["date"] == "2025-05-13"
    assert item["net_volume"] == 1500000.0
    assert item["buy_volume"] == 2000000.0
    assert item["sell_volume"] == 500000.0


@pytest.mark.asyncio
async def test_get_sector_flow_negative_net_volume(mock_db_session):
    """Net volume can be negative (more selling than buying)."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        _make_flow_row("Bất động sản", date(2025, 5, 14), -800000.0, 100000.0, 900000.0),
    ]
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_flow(
        date(2025, 5, 14), date(2025, 5, 14)
    )

    assert len(result) == 1
    assert result[0]["net_volume"] == -800000.0
    assert result[0]["sell_volume"] == 900000.0


@pytest.mark.asyncio
async def test_get_sector_flow_empty_result(mock_db_session):
    """Empty date range returns empty list."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_flow(
        date(2099, 1, 1), date(2099, 12, 31)
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_sector_performance_single_ticker_sector(mock_db_session):
    """Sectors with only 1 ticker still work correctly."""
    from app.services.sector_analysis_service import SectorAnalysisService

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        _make_perf_row("Dầu khí", 1, 2.0, 5.0, -3.0),
    ]
    mock_db_session.execute.return_value = mock_result

    service = SectorAnalysisService(mock_db_session)
    result = await service.get_sector_performance(
        date(2025, 5, 1), date(2025, 5, 14)
    )

    assert len(result) == 1
    assert result[0]["ticker_count"] == 1
    assert result[0]["avg_change_today"] == 2.0
