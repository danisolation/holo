"""Tests for CSV import service: format detection, parsing, validation, import.

Covers PORT-12 requirements: VNDirect/SSI format detection, row validation, dry-run preview.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import date, datetime


# Sample CSV content for testing
VNDIRECT_CSV = '''"Mã CK","Loại GD","Khối lượng","Giá","Ngày GD","Phí GD"
"VNM","Mua","100","80000","15/01/2024","50000"
"FPT","Bán","50","120000","20/01/2024","30000"
'''

SSI_CSV = '''"Symbol","Side","Quantity","Price","Trade Date","Fees"
"VNM","BUY","100","80000","2024-01-15","50000"
"FPT","SELL","50","120000","2024-01-20","30000"
'''

UNKNOWN_CSV = '''"Col1","Col2","Col3"
"val1","val2","val3"
'''


class TestCSVFormatDetection:
    """Test CSV format auto-detection by header row."""

    @pytest.mark.asyncio
    async def test_detect_vndirect_format(self):
        """Headers with 'Mã CK' + 'Khối lượng' → VNDirect."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        header = ["Mã CK", "Loại GD", "Khối lượng", "Giá", "Ngày GD", "Phí GD"]
        result = svc.detect_format(header)
        assert result == "VNDirect"

    @pytest.mark.asyncio
    async def test_detect_vndirect_format_alt_header(self):
        """Headers with 'Mã chứng khoán' → VNDirect."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        header = ["Mã chứng khoán", "Loại GD", "KL", "Giá", "Ngày GD", "Phí GD"]
        result = svc.detect_format(header)
        assert result == "VNDirect"

    @pytest.mark.asyncio
    async def test_detect_ssi_format(self):
        """Headers with 'Symbol' + 'Quantity' → SSI."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        header = ["Symbol", "Side", "Quantity", "Price", "Trade Date", "Fees"]
        result = svc.detect_format(header)
        assert result == "SSI"

    @pytest.mark.asyncio
    async def test_detect_unknown_format(self):
        """Unrecognized headers → 'unknown'."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        header = ["Col1", "Col2", "Col3"]
        result = svc.detect_format(header)
        assert result == "unknown"


class TestCSVParsing:
    """Test CSV row parsing for VNDirect and SSI formats."""

    @pytest.mark.asyncio
    async def test_parse_rows_vndirect(self):
        """VNDirect CSV parsed with Vietnamese column mapping."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        fmt, rows = svc.parse_rows(VNDIRECT_CSV)
        assert fmt == "VNDirect"
        assert len(rows) == 2

        # First row
        assert rows[0]["symbol"] == "VNM"
        assert rows[0]["side"] == "BUY"  # Mua → BUY
        assert rows[0]["quantity"] == 100
        assert rows[0]["price"] == 80000.0
        assert rows[0]["trade_date"] == "2024-01-15"
        assert rows[0]["fees"] == 50000.0

        # Second row
        assert rows[1]["symbol"] == "FPT"
        assert rows[1]["side"] == "SELL"  # Bán → SELL
        assert rows[1]["quantity"] == 50

    @pytest.mark.asyncio
    async def test_parse_rows_ssi(self):
        """SSI CSV parsed with English column mapping."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        fmt, rows = svc.parse_rows(SSI_CSV)
        assert fmt == "SSI"
        assert len(rows) == 2

        assert rows[0]["symbol"] == "VNM"
        assert rows[0]["side"] == "BUY"
        assert rows[0]["quantity"] == 100
        assert rows[0]["price"] == 80000.0
        assert rows[0]["trade_date"] == "2024-01-15"
        assert rows[0]["fees"] == 50000.0

    @pytest.mark.asyncio
    async def test_parse_rows_unknown_format_raises(self):
        """Unknown CSV format → ValueError."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        with pytest.raises(ValueError, match="Unrecognized CSV format"):
            svc.parse_rows(UNKNOWN_CSV)


class TestCSVValidation:
    """Test row-level validation for CSV imports."""

    @pytest.mark.asyncio
    async def test_validate_rows_unknown_symbol_error(self):
        """Unknown symbols marked as error."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        # Mock ticker query: only VNM exists
        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        rows = [
            {"symbol": "VNM", "side": "BUY", "quantity": 100, "price": 80000, "trade_date": "2024-01-15", "fees": 0},
            {"symbol": "FAKE", "side": "BUY", "quantity": 50, "price": 10000, "trade_date": "2024-01-15", "fees": 0},
        ]

        result = await svc.validate_rows(rows)
        assert result[0].status == "valid"
        assert result[1].status == "error"
        assert "not found" in result[1].message.lower()

    @pytest.mark.asyncio
    async def test_validate_rows_negative_quantity_error(self):
        """Negative quantity marked as error."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        rows = [
            {"symbol": "VNM", "side": "BUY", "quantity": -10, "price": 80000, "trade_date": "2024-01-15", "fees": 0},
        ]

        result = await svc.validate_rows(rows)
        assert result[0].status == "error"
        assert "quantity" in result[0].message.lower()

    @pytest.mark.asyncio
    async def test_validate_rows_duplicate_warning(self):
        """Duplicate rows (same date+symbol+side+qty) → warning."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        rows = [
            {"symbol": "VNM", "side": "BUY", "quantity": 100, "price": 80000, "trade_date": "2024-01-15", "fees": 0},
            {"symbol": "VNM", "side": "BUY", "quantity": 100, "price": 80000, "trade_date": "2024-01-15", "fees": 0},
        ]

        result = await svc.validate_rows(rows)
        assert result[0].status == "valid"
        assert result[1].status == "warning"
        assert "duplicate" in result[1].message.lower()

    @pytest.mark.asyncio
    async def test_validate_rows_future_date_error(self):
        """Future trade_date marked as error."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        rows = [
            {"symbol": "VNM", "side": "BUY", "quantity": 100, "price": 80000, "trade_date": "2099-01-15", "fees": 0},
        ]

        result = await svc.validate_rows(rows)
        assert result[0].status == "error"
        assert "future" in result[0].message.lower()

    @pytest.mark.asyncio
    async def test_validate_rows_invalid_side_error(self):
        """Invalid side (not BUY/SELL) → error."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        rows = [
            {"symbol": "VNM", "side": "HOLD", "quantity": 100, "price": 80000, "trade_date": "2024-01-15", "fees": 0},
        ]

        result = await svc.validate_rows(rows)
        assert result[0].status == "error"
        assert "side" in result[0].message.lower()


class TestCSVDryRun:
    """Test CSV dry-run preview."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_correct_counts(self):
        """dry_run returns CSVDryRunResponse with correct valid/warning/error counts."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        # Mock ticker query: only VNM exists
        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        # VNDirect CSV with VNM (valid) and FPT (error - not found)
        csv_content = '''"Mã CK","Loại GD","Khối lượng","Giá","Ngày GD","Phí GD"
"VNM","Mua","100","80000","15/01/2024","50000"
"FPT","Bán","50","120000","20/01/2024","30000"
'''

        result = await svc.dry_run(csv_content)
        assert result.format_detected == "VNDirect"
        assert len(result.rows) == 2
        assert result.total_valid == 1
        assert result.total_errors == 1


class TestCSVImport:
    """Test CSV import with trade recording."""

    @pytest.mark.asyncio
    async def test_import_trades_records_valid_rows(self):
        """import_trades calls record_trade for each valid row."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        # Mock ticker query
        ticker_vnm = MagicMock()
        ticker_vnm.symbol = "VNM"
        ticker_fpt = MagicMock()
        ticker_fpt.symbol = "FPT"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker_vnm, ticker_fpt]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        # Mock PortfolioService.record_trade
        mock_portfolio_svc = AsyncMock()
        mock_portfolio_svc.record_trade = AsyncMock(return_value={"id": 1})

        result = await svc.import_trades(SSI_CSV, mock_portfolio_svc)
        assert result["trades_imported"] == 2
        assert mock_portfolio_svc.record_trade.await_count == 2

    @pytest.mark.asyncio
    async def test_import_trades_skips_error_rows(self):
        """import_trades skips rows with validation errors."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        # Mock ticker query: only VNM exists (FPT not found)
        ticker = MagicMock()
        ticker.symbol = "VNM"
        ticker_result = MagicMock()
        ticker_result.scalars.return_value.all.return_value = [ticker]
        svc.session.execute = AsyncMock(return_value=ticker_result)

        mock_portfolio_svc = AsyncMock()
        mock_portfolio_svc.record_trade = AsyncMock(return_value={"id": 1})

        result = await svc.import_trades(SSI_CSV, mock_portfolio_svc)
        # Only VNM is valid, FPT is error
        assert result["trades_imported"] == 1
        assert mock_portfolio_svc.record_trade.await_count == 1

    @pytest.mark.asyncio
    async def test_import_rejects_over_1000_rows(self):
        """T-13-05 mitigation: CSV with > 1000 data rows → ValueError."""
        from app.services.csv_import_service import CSVImportService

        svc = CSVImportService.__new__(CSVImportService)
        svc.session = AsyncMock()

        # Build CSV with 1001 data rows
        header = '"Symbol","Side","Quantity","Price","Trade Date","Fees"\n'
        rows = '"VNM","BUY","100","80000","2024-01-15","0"\n' * 1001
        csv_content = header + rows

        mock_portfolio_svc = AsyncMock()

        with pytest.raises(ValueError, match="1000"):
            await svc.import_trades(csv_content, mock_portfolio_svc)
