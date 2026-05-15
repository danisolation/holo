"""Unit tests for ScreenerService.

Tests cover:
- screen_tickers returns correct structure with pagination
- screen_tickers applies sector filter
- screen_tickers sorting by different columns
- screen_tickers pagination offset/limit
- get_peer_comparison highlights target ticker
- get_peer_comparison assigns ranks (1-based)
- get_sector_detail returns tickers with change_7d/change_30d
- get_peer_comparison raises ValueError when ticker has no sector
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_ticker(tid, symbol, name, sector="Ngân hàng", industry="Ngân hàng thương mại", market_cap=50000):
    """Create a mock Ticker object."""
    t = MagicMock()
    t.id = tid
    t.symbol = symbol
    t.name = name
    t.sector = sector
    t.industry = industry
    t.market_cap = Decimal(str(market_cap)) if market_cap else None
    t.is_active = True
    return t


def _make_price_row(ticker_id, dt, close, volume):
    """Create a mock DailyPrice row."""
    row = MagicMock()
    row.ticker_id = ticker_id
    row.date = dt
    row.close = Decimal(str(close))
    row.volume = volume
    return row


def _make_financial_row(ticker_id, pe):
    """Create a mock Financial row for P/E lookup."""
    row = MagicMock()
    row.ticker_id = ticker_id
    row.pe = Decimal(str(pe)) if pe is not None else None
    return row


@pytest.mark.asyncio
async def test_screen_tickers_returns_correct_structure(mock_db_session):
    """screen_tickers returns dict with items, total, offset, limit."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    # Mock _get_active_tickers
    tickers = [
        _make_ticker(1, "VCB", "Vietcombank"),
        _make_ticker(2, "TCB", "Techcombank"),
    ]

    with patch.object(service, "_get_active_tickers", return_value=tickers), \
         patch.object(service, "_get_latest_prices", return_value={
             1: {"close": 95.0, "volume": 1000000, "date": date(2025, 5, 14)},
             2: {"close": 48.0, "volume": 500000, "date": date(2025, 5, 14)},
         }), \
         patch.object(service, "_get_historical_closes", return_value={
             1: [(date(2025, 5, 14), 95.0), (date(2025, 5, 13), 93.0)],
             2: [(date(2025, 5, 14), 48.0), (date(2025, 5, 13), 47.0)],
         }), \
         patch.object(service, "_get_latest_pe", return_value={1: 12.5, 2: 8.3}):

        result = await service.screen_tickers()

    assert "items" in result
    assert "total" in result
    assert "offset" in result
    assert "limit" in result
    assert result["total"] == 2
    assert len(result["items"]) == 2
    item = result["items"][0]
    assert "symbol" in item
    assert "close" in item
    assert "volume" in item
    assert "change_1d" in item
    assert "pe" in item


@pytest.mark.asyncio
async def test_screen_tickers_applies_sector_filter(mock_db_session):
    """screen_tickers passes sector filter to _get_active_tickers."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    with patch.object(service, "_get_active_tickers", return_value=[]) as mock_get:
        result = await service.screen_tickers(sector="Ngân hàng")

    mock_get.assert_called_once_with("Ngân hàng", None)
    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_screen_tickers_sorting(mock_db_session):
    """screen_tickers sorts by specified column and order."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    tickers = [
        _make_ticker(1, "VCB", "Vietcombank", market_cap=100000),
        _make_ticker(2, "TCB", "Techcombank", market_cap=50000),
        _make_ticker(3, "BID", "BIDV", market_cap=80000),
    ]

    with patch.object(service, "_get_active_tickers", return_value=tickers), \
         patch.object(service, "_get_latest_prices", return_value={
             1: {"close": 95.0, "volume": 1000000, "date": date(2025, 5, 14)},
             2: {"close": 48.0, "volume": 2000000, "date": date(2025, 5, 14)},
             3: {"close": 45.0, "volume": 1500000, "date": date(2025, 5, 14)},
         }), \
         patch.object(service, "_get_historical_closes", return_value={}), \
         patch.object(service, "_get_latest_pe", return_value={}):

        # Sort by volume desc (default)
        result = await service.screen_tickers(sort_by="volume", sort_order="desc")

    symbols = [i["symbol"] for i in result["items"]]
    assert symbols[0] == "TCB"  # highest volume


@pytest.mark.asyncio
async def test_screen_tickers_pagination(mock_db_session):
    """screen_tickers respects offset and limit."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    tickers = [_make_ticker(i, f"T{i}", f"Ticker {i}") for i in range(1, 6)]

    with patch.object(service, "_get_active_tickers", return_value=tickers), \
         patch.object(service, "_get_latest_prices", return_value={
             i: {"close": 10.0, "volume": i * 100, "date": date(2025, 5, 14)}
             for i in range(1, 6)
         }), \
         patch.object(service, "_get_historical_closes", return_value={}), \
         patch.object(service, "_get_latest_pe", return_value={}):

        result = await service.screen_tickers(limit=2, offset=1)

    assert result["total"] == 5
    assert result["offset"] == 1
    assert result["limit"] == 2
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_get_peer_comparison_highlights_target(mock_db_session):
    """get_peer_comparison marks target ticker with is_target=True."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    target_ticker = _make_ticker(1, "VCB", "Vietcombank")
    peers = [
        target_ticker,
        _make_ticker(2, "TCB", "Techcombank"),
    ]

    # Mock the direct DB call for finding the target ticker
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = target_ticker
    mock_db_session.execute.return_value = mock_result

    with patch.object(service, "_get_active_tickers", return_value=peers), \
         patch.object(service, "_get_latest_prices", return_value={
             1: {"close": 95.0, "volume": 1000000, "date": date(2025, 5, 14)},
             2: {"close": 48.0, "volume": 500000, "date": date(2025, 5, 14)},
         }), \
         patch.object(service, "_get_historical_closes", return_value={
             1: [(date(2025, 5, 14), 95.0), (date(2025, 5, 13), 93.0)],
             2: [(date(2025, 5, 14), 48.0), (date(2025, 5, 13), 47.0)],
         }), \
         patch.object(service, "_get_latest_pe", return_value={1: 12.5, 2: 8.3}):

        result = await service.get_peer_comparison("VCB")

    assert result["symbol"] == "VCB"
    assert result["sector"] == "Ngân hàng"
    target_peers = [p for p in result["peers"] if p["is_target"]]
    assert len(target_peers) == 1
    assert target_peers[0]["symbol"] == "VCB"


@pytest.mark.asyncio
async def test_get_peer_comparison_ranks_metrics(mock_db_session):
    """get_peer_comparison assigns 1-based ranks to metrics."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    target_ticker = _make_ticker(1, "VCB", "Vietcombank")
    peers = [
        target_ticker,
        _make_ticker(2, "TCB", "Techcombank"),
        _make_ticker(3, "BID", "BIDV"),
    ]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = target_ticker
    mock_db_session.execute.return_value = mock_result

    with patch.object(service, "_get_active_tickers", return_value=peers), \
         patch.object(service, "_get_latest_prices", return_value={
             1: {"close": 95.0, "volume": 3000000, "date": date(2025, 5, 14)},
             2: {"close": 48.0, "volume": 1000000, "date": date(2025, 5, 14)},
             3: {"close": 45.0, "volume": 2000000, "date": date(2025, 5, 14)},
         }), \
         patch.object(service, "_get_historical_closes", return_value={
             1: [(date(2025, 5, 14), 95.0), (date(2025, 5, 13), 90.0)],
             2: [(date(2025, 5, 14), 48.0), (date(2025, 5, 13), 47.0)],
             3: [(date(2025, 5, 14), 45.0), (date(2025, 5, 13), 44.0)],
         }), \
         patch.object(service, "_get_latest_pe", return_value={1: 15.0, 2: 8.0, 3: 12.0}):

        result = await service.get_peer_comparison("VCB")

    # Check ranks exist and are 1-based integers
    for peer in result["peers"]:
        assert peer["rank_pe"] is not None
        assert peer["rank_volume"] is not None
        assert peer["rank_change"] is not None
        assert peer["rank_market_cap"] is not None
        assert isinstance(peer["rank_pe"], int)
        assert peer["rank_pe"] >= 1

    # TCB has lowest P/E (8.0) → rank_pe = 1
    tcb = [p for p in result["peers"] if p["symbol"] == "TCB"][0]
    assert tcb["rank_pe"] == 1

    # VCB has highest volume (3M) → rank_volume = 1
    vcb = [p for p in result["peers"] if p["symbol"] == "VCB"][0]
    assert vcb["rank_volume"] == 1


@pytest.mark.asyncio
async def test_get_sector_detail_returns_tickers(mock_db_session):
    """get_sector_detail returns sector tickers with change_7d/change_30d."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    tickers = [
        _make_ticker(1, "VCB", "Vietcombank"),
        _make_ticker(2, "TCB", "Techcombank"),
    ]

    with patch.object(service, "_get_active_tickers", return_value=tickers), \
         patch.object(service, "_get_latest_prices", return_value={
             1: {"close": 95.0, "volume": 1000000, "date": date(2025, 5, 14)},
             2: {"close": 48.0, "volume": 500000, "date": date(2025, 5, 14)},
         }), \
         patch.object(service, "_get_historical_closes", return_value={
             1: [(date(2025, 5, 14) - timedelta(days=i), 90.0 + i) for i in range(25)],
             2: [(date(2025, 5, 14) - timedelta(days=i), 46.0 + i * 0.1) for i in range(25)],
         }):

        result = await service.get_sector_detail("Ngân hàng")

    assert result["sector"] == "Ngân hàng"
    assert result["ticker_count"] == 2
    assert len(result["tickers"]) == 2

    item = result["tickers"][0]
    assert "symbol" in item
    assert "change_7d" in item
    assert "change_30d" in item
    assert "close" in item
    assert "volume" in item


@pytest.mark.asyncio
async def test_get_peer_comparison_no_sector_raises(mock_db_session):
    """get_peer_comparison raises ValueError if ticker has no sector."""
    from app.services.screener_service import ScreenerService

    service = ScreenerService(mock_db_session)

    no_sector_ticker = _make_ticker(1, "XYZ", "No Sector Corp", sector=None)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = no_sector_ticker
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(ValueError, match="no sector"):
        await service.get_peer_comparison("XYZ")
