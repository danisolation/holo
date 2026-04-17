"""CSV import service: parse VNDirect/SSI broker exports into trades.

Per PORT-12: auto-detect format, validate, dry-run preview, commit.
T-13-04 mitigation: server-side validation of every row.
T-13-05 mitigation: max 1000 rows per CSV file.
"""
import csv
import io
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticker import Ticker
from app.schemas.portfolio import CSVPreviewRow, CSVDryRunResponse

# T-13-05: Max rows per CSV import
MAX_CSV_ROWS = 1000


class CSVImportService:
    """Parse and import VNDirect/SSI broker CSV exports."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def detect_format(self, header: list[str]) -> str:
        """Detect CSV format from header row.

        Returns 'VNDirect', 'SSI', or 'unknown'.
        """
        header_lower = [h.strip().lower() for h in header]

        # VNDirect indicators
        has_ma_ck = any(
            "mã ck" in h or "mã chứng khoán" in h for h in header_lower
        )
        has_kl = any("khối lượng" in h or "kl" == h for h in header_lower)
        if has_ma_ck and has_kl:
            return "VNDirect"

        # SSI indicators (English headers)
        has_symbol = any("symbol" == h for h in header_lower)
        has_quantity = any("quantity" == h for h in header_lower)
        if has_symbol and has_quantity:
            return "SSI"

        return "unknown"

    def parse_rows(self, content: str) -> tuple[str, list[dict]]:
        """Parse CSV string, detect format, map columns to standard fields.

        Returns (format_detected, list of row dicts).
        Raises ValueError if format is unrecognized.
        """
        reader = csv.reader(io.StringIO(content.strip()))
        header = next(reader)
        header = [h.strip() for h in header]

        fmt = self.detect_format(header)
        if fmt == "unknown":
            raise ValueError("Unrecognized CSV format")

        rows = []
        for csv_row in reader:
            if not any(cell.strip() for cell in csv_row):
                continue  # Skip empty rows

            if fmt == "VNDirect":
                row = self._parse_vndirect_row(header, csv_row)
            else:
                row = self._parse_ssi_row(header, csv_row)

            rows.append(row)

        return fmt, rows

    def _parse_vndirect_row(self, header: list[str], csv_row: list[str]) -> dict:
        """Map VNDirect Vietnamese columns to standard fields."""
        col_map = {}
        header_lower = [h.strip().lower() for h in header]
        for i, h in enumerate(header_lower):
            if "mã ck" in h or "mã chứng khoán" in h:
                col_map["symbol"] = i
            elif "loại gd" in h:
                col_map["side"] = i
            elif "khối lượng" in h or h == "kl":
                col_map["quantity"] = i
            elif "giá" == h or "giá" in h:
                col_map["price"] = i
            elif "ngày gd" in h:
                col_map["trade_date"] = i
            elif "phí gd" in h or "phí" in h:
                col_map["fees"] = i

        values = [v.strip() for v in csv_row]

        # Parse side: Mua → BUY, Bán → SELL
        raw_side = values[col_map["side"]].strip()
        side = "BUY" if raw_side.lower() in ("mua", "buy") else "SELL"

        # Parse date DD/MM/YYYY → YYYY-MM-DD
        raw_date = values[col_map["trade_date"]].strip()
        parsed_date = datetime.strptime(raw_date, "%d/%m/%Y").date()

        return {
            "symbol": values[col_map["symbol"]].strip().upper(),
            "side": side,
            "quantity": int(values[col_map["quantity"]]),
            "price": float(values[col_map["price"]]),
            "trade_date": parsed_date.isoformat(),
            "fees": float(values[col_map.get("fees", -1)]) if "fees" in col_map else 0.0,
        }

    def _parse_ssi_row(self, header: list[str], csv_row: list[str]) -> dict:
        """Map SSI English columns to standard fields."""
        col_map = {}
        header_lower = [h.strip().lower() for h in header]
        for i, h in enumerate(header_lower):
            if h == "symbol":
                col_map["symbol"] = i
            elif h == "side":
                col_map["side"] = i
            elif h == "quantity":
                col_map["quantity"] = i
            elif h == "price":
                col_map["price"] = i
            elif h == "trade date":
                col_map["trade_date"] = i
            elif h == "fees":
                col_map["fees"] = i

        values = [v.strip() for v in csv_row]

        # Parse date YYYY-MM-DD
        raw_date = values[col_map["trade_date"]].strip()
        parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").date()

        return {
            "symbol": values[col_map["symbol"]].strip().upper(),
            "side": values[col_map["side"]].strip().upper(),
            "quantity": int(values[col_map["quantity"]]),
            "price": float(values[col_map["price"]]),
            "trade_date": parsed_date.isoformat(),
            "fees": float(values[col_map.get("fees", -1)]) if "fees" in col_map else 0.0,
        }

    async def validate_rows(self, rows: list[dict]) -> list[CSVPreviewRow]:
        """Validate each row and return CSVPreviewRow with status.

        T-13-04 mitigation: check symbol exists, quantity > 0, price > 0,
        date not future, side is BUY/SELL.
        """
        # Batch query all unique symbols
        symbols = list({r["symbol"] for r in rows})
        result = await self.session.execute(
            select(Ticker).where(Ticker.symbol.in_(symbols))
        )
        valid_symbols = {t.symbol for t in result.scalars().all()}

        today = date.today()
        seen_keys: set[tuple] = set()
        preview_rows: list[CSVPreviewRow] = []

        for i, row in enumerate(rows):
            status = "valid"
            message = None

            # Check symbol exists
            if row["symbol"] not in valid_symbols:
                status = "error"
                message = f"Symbol '{row['symbol']}' not found in database"
            # Check quantity > 0
            elif row["quantity"] <= 0:
                status = "error"
                message = f"Quantity must be > 0, got {row['quantity']}"
            # Check price > 0
            elif row["price"] <= 0:
                status = "error"
                message = f"Price must be > 0, got {row['price']}"
            # Check side
            elif row["side"] not in ("BUY", "SELL"):
                status = "error"
                message = f"Side must be BUY or SELL, got '{row['side']}'"
            # Check future date
            elif datetime.strptime(row["trade_date"], "%Y-%m-%d").date() > today:
                status = "error"
                message = f"Trade date {row['trade_date']} is in the future"
            else:
                # Check duplicate
                key = (row["trade_date"], row["symbol"], row["side"], row["quantity"])
                if key in seen_keys:
                    status = "warning"
                    message = "Possible duplicate row (same date+symbol+side+quantity)"
                else:
                    seen_keys.add(key)

            preview_rows.append(
                CSVPreviewRow(
                    row_number=i + 1,
                    symbol=row["symbol"],
                    side=row["side"],
                    quantity=row["quantity"],
                    price=row["price"],
                    trade_date=row["trade_date"],
                    fees=row.get("fees", 0),
                    status=status,
                    message=message,
                )
            )

        return preview_rows

    async def dry_run(self, content: str) -> CSVDryRunResponse:
        """Parse and validate CSV, return preview without importing.

        Returns CSVDryRunResponse with per-row status and summary counts.
        """
        fmt, rows = self.parse_rows(content)
        preview_rows = await self.validate_rows(rows)

        total_valid = sum(1 for r in preview_rows if r.status == "valid")
        total_warnings = sum(1 for r in preview_rows if r.status == "warning")
        total_errors = sum(1 for r in preview_rows if r.status == "error")

        return CSVDryRunResponse(
            format_detected=fmt,
            rows=preview_rows,
            total_valid=total_valid,
            total_warnings=total_warnings,
            total_errors=total_errors,
        )

    async def import_trades(self, content: str, portfolio_service) -> dict:
        """Parse, validate, and import valid trades atomically.

        T-13-05 mitigation: rejects CSV with > 1000 data rows.
        All trades are imported within a single transaction — if any trade
        fails, all previously inserted trades in this batch are rolled back.
        Returns {"trades_imported": N, "tickers_recalculated": M}.
        """
        fmt, rows = self.parse_rows(content)

        # T-13-05: Max rows check
        if len(rows) > MAX_CSV_ROWS:
            raise ValueError(
                f"CSV contains {len(rows)} data rows, maximum is {MAX_CSV_ROWS}"
            )

        preview_rows = await self.validate_rows(rows)

        trades_imported = 0
        ticker_ids: set[str] = set()

        try:
            for row, preview in zip(rows, preview_rows):
                if preview.status == "error":
                    continue

                trade_date = datetime.strptime(row["trade_date"], "%Y-%m-%d").date()
                await portfolio_service.record_trade(
                    symbol=row["symbol"],
                    side=row["side"],
                    quantity=row["quantity"],
                    price=row["price"],
                    trade_date=trade_date,
                    fees=row.get("fees", 0),
                    auto_commit=False,
                )
                trades_imported += 1
                ticker_ids.add(row["symbol"])

            # Single commit for all trades — atomic
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return {
            "trades_imported": trades_imported,
            "tickers_recalculated": len(ticker_ids),
        }
