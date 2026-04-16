"""Technical indicator computation and storage service.

Computes RSI(14), MACD(12,26,9), SMA(20/50/200), EMA(12/26), BB(20,2)
using the ta library. Stores results in technical_indicators table.

Key decisions (from CONTEXT.md):
- Compute for most recent 60 days per run (settings.indicator_compute_days)
- Only compute new/missing dates (query MAX(date) per ticker)
- NaN warm-up values → NULL in PostgreSQL (fillna=False)
- SMA(200) needs 200+ rows; skip tickers with < 20 rows
"""
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands

from app.config import settings
from app.models.daily_price import DailyPrice
from app.models.technical_indicator import TechnicalIndicator
from app.services.ticker_service import TickerService


class IndicatorService:
    """Compute and store technical indicators for all tickers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def compute_all_tickers(self) -> dict:
        """Compute indicators for all active tickers.

        Returns: {success: int, failed: int, skipped: int, failed_symbols: list[str]}
        """
        ticker_service = TickerService(self.session)
        ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Computing indicators for {len(ticker_map)} active tickers")

        success = 0
        failed = 0
        skipped = 0
        failed_symbols: list[str] = []

        for symbol, ticker_id in ticker_map.items():
            try:
                rows_stored = await self.compute_for_ticker(ticker_id, symbol)
                if rows_stored == 0:
                    skipped += 1
                else:
                    success += 1
                    logger.debug(f"{symbol}: {rows_stored} indicator rows stored")
            except Exception as e:
                logger.error(f"{symbol}: Indicator computation failed — {type(e).__name__}: {e}")
                failed += 1
                failed_symbols.append(symbol)

        await self.session.commit()

        result = {
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"Indicator computation complete: {result}")
        return result

    async def compute_for_ticker(self, ticker_id: int, symbol: str) -> int:
        """Compute indicators for a single ticker. Returns rows stored."""
        # Fetch price history ordered by date ASC
        result = await self.session.execute(
            select(DailyPrice.date, DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date)
        )
        rows = result.fetchall()

        if len(rows) < 20:
            logger.warning(f"{symbol}: Only {len(rows)} price rows, need ≥20 for indicators — skipping")
            return 0

        df = pd.DataFrame(rows, columns=["date", "close"])
        df["close"] = df["close"].astype(float)

        # Compute all 12 indicators
        indicators = self._compute_indicators(df["close"])

        # Find last computed date to only store new rows (incremental)
        last_computed = await self._get_last_computed_date(ticker_id)

        # Limit to most recent indicator_compute_days dates
        compute_days = settings.indicator_compute_days
        start_idx = max(0, len(df) - compute_days)

        bulk_rows = []
        for i in range(start_idx, len(df)):
            row_date = df["date"].iloc[i]
            if isinstance(row_date, pd.Timestamp):
                row_date = row_date.date()

            if last_computed and row_date <= last_computed:
                continue

            values: dict = {
                "ticker_id": ticker_id,
                "date": row_date,
            }
            for col_name, series in indicators.items():
                values[col_name] = self._safe_decimal(series.iloc[i])
            bulk_rows.append(values)

        if not bulk_rows:
            return 0

        stmt = insert(TechnicalIndicator).values(bulk_rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_technical_indicators_ticker_date",
            set_={k: stmt.excluded[k] for k in bulk_rows[0] if k not in ("ticker_id", "date")},
        )
        await self.session.execute(stmt)
        return len(bulk_rows)

    def _compute_indicators(self, close: pd.Series) -> dict[str, pd.Series]:
        """Pure computation — all 12 indicators from close prices.

        Uses fillna=False so NaN stays as NaN (stored as NULL in PostgreSQL).
        Instantiates each ta class once for efficiency.
        """
        rsi = RSIIndicator(close=close, window=14, fillna=False)
        macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False)
        sma20 = SMAIndicator(close=close, window=20, fillna=False)
        sma50 = SMAIndicator(close=close, window=50, fillna=False)
        sma200 = SMAIndicator(close=close, window=200, fillna=False)
        ema12 = EMAIndicator(close=close, window=12, fillna=False)
        ema26 = EMAIndicator(close=close, window=26, fillna=False)
        bb = BollingerBands(close=close, window=20, window_dev=2, fillna=False)

        return {
            "rsi_14": rsi.rsi(),
            "macd_line": macd.macd(),
            "macd_signal": macd.macd_signal(),
            "macd_histogram": macd.macd_diff(),
            "sma_20": sma20.sma_indicator(),
            "sma_50": sma50.sma_indicator(),
            "sma_200": sma200.sma_indicator(),
            "ema_12": ema12.ema_indicator(),
            "ema_26": ema26.ema_indicator(),
            "bb_upper": bb.bollinger_hband(),
            "bb_middle": bb.bollinger_mavg(),
            "bb_lower": bb.bollinger_lband(),
        }

    async def _get_last_computed_date(self, ticker_id: int) -> date | None:
        """Get last computed indicator date for a ticker."""
        result = await self.session.execute(
            select(func.max(TechnicalIndicator.date))
            .where(TechnicalIndicator.ticker_id == ticker_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _safe_decimal(value) -> Decimal | None:
        """Convert float to Decimal, NaN→None.

        Uses round(value, 6) to avoid float precision issues
        (e.g., Decimal(0.3) → '0.30000000000000004').
        """
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return Decimal(str(round(value, 6)))
        except (InvalidOperation, ValueError, TypeError):
            return None
