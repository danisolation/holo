"""Financial ratio crawling and storage service.

Fetches P/E, P/B, EPS, ROE, ROA, growth rates,
current_ratio, and debt_to_equity from vnstock finance.ratio().

WARNING: vnstock Finance.__init__() triggers an extra API call per ticker
to determine com_type_code. Factor this into rate limiting.
"""
import asyncio
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.models.financial import Financial
from app.services.ticker_service import TickerService


class FinancialService:
    """Manages financial ratio data crawling and storage."""

    def __init__(self, session: AsyncSession, crawler: VnstockCrawler | None = None):
        self.session = session
        self.crawler = crawler or VnstockCrawler()
        self.ticker_service = TickerService(session, self.crawler)

    async def crawl_financials(self, period: str = "quarter") -> dict:
        """Crawl financial ratios for all active tickers.

        Args:
            period: 'quarter' or 'annual'

        Returns: {success: int, failed: int, failed_symbols: list[str]}
        """
        ticker_map = await self.ticker_service.get_ticker_id_map()
        symbols = list(ticker_map.keys())
        logger.info(f"Starting financial crawl for {len(symbols)} tickers ({period})")

        success = 0
        failed = 0
        failed_symbols = []
        batch_size = settings.crawl_batch_size

        for batch_start in range(0, len(symbols), batch_size):
            batch = symbols[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            logger.info(f"Financial batch {batch_num}/{total_batches} ({len(batch)} tickers)")

            for symbol in batch:
                try:
                    df = await self.crawler.fetch_financial_ratios(symbol, period=period)

                    if df is None or df.empty:
                        logger.warning(f"{symbol}: No financial data returned")
                        failed += 1
                        failed_symbols.append(symbol)
                        await asyncio.sleep(settings.crawl_delay_seconds)
                        continue

                    rows_stored = await self._store_financials(
                        symbol, ticker_map[symbol], df, period
                    )
                    success += 1
                    logger.debug(f"{symbol}: {rows_stored} financial periods stored")

                except Exception as e:
                    logger.error(f"{symbol}: Financial crawl failed — {type(e).__name__}: {e}")
                    failed += 1
                    failed_symbols.append(symbol)

                # Extra delay for financials (Finance.__init__ makes extra API call)
                await asyncio.sleep(settings.crawl_delay_seconds)

        await self.session.commit()

        result = {"success": success, "failed": failed, "failed_symbols": failed_symbols}
        logger.info(f"Financial crawl complete: {result}")
        return result

    async def _store_financials(
        self, symbol: str, ticker_id: int, df: pd.DataFrame, period_type: str
    ) -> int:
        """Store financial ratios DataFrame into financials table.

        vnstock finance.ratio() returns a MultiIndex DataFrame.
        We flatten it and extract the key metrics per period.
        Uses INSERT ... ON CONFLICT (ticker_id, period) DO UPDATE.
        """
        rows_stored = 0

        # finance.ratio() may return MultiIndex or flat DataFrame depending on version
        # Reset index to get flat columns
        if isinstance(df.columns, pd.MultiIndex):
            df = df.T  # Transpose if MultiIndex columns represent periods
            df = df.reset_index()

        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()

        # Try to iterate over periods in the DataFrame
        # The exact structure depends on vnstock version; handle gracefully
        for idx, row in df.iterrows():
            try:
                year_val = self._safe_int(row.get("year", row.get("Year", None)))
                quarter_val = self._safe_int(row.get("quarter", row.get("Quarter", None)))

                if year_val is None:
                    continue  # Skip rows without year info

                if quarter_val is not None:
                    period_str = f"Q{quarter_val}-{year_val}"
                else:
                    period_str = f"Y-{year_val}"

                stmt = insert(Financial).values(
                    ticker_id=ticker_id,
                    period=period_str,
                    year=year_val,
                    quarter=quarter_val,
                    pe=self._safe_decimal(row.get("pe", row.get("PE", None))),
                    pb=self._safe_decimal(row.get("pb", row.get("PB", None))),
                    eps=self._safe_decimal(row.get("eps", row.get("EPS", None))),
                    roe=self._safe_decimal(row.get("roe", row.get("ROE", None))),
                    roa=self._safe_decimal(row.get("roa", row.get("ROA", None))),
                    revenue_growth=self._safe_decimal(
                        row.get("revenue_growth", row.get("revenueGrowth", None))
                    ),
                    profit_growth=self._safe_decimal(
                        row.get("profit_growth", row.get("netProfitGrowth", None))
                    ),
                    current_ratio=self._safe_decimal(
                        row.get("current_ratio", row.get("currentRatio", None))
                    ),
                    debt_to_equity=self._safe_decimal(
                        row.get("debt_to_equity", row.get("debtToEquity", None))
                    ),
                ).on_conflict_do_update(
                    constraint="uq_financials_ticker_period",
                    set_={
                        "pe": self._safe_decimal(row.get("pe", row.get("PE", None))),
                        "pb": self._safe_decimal(row.get("pb", row.get("PB", None))),
                        "eps": self._safe_decimal(row.get("eps", row.get("EPS", None))),
                        "roe": self._safe_decimal(row.get("roe", row.get("ROE", None))),
                        "roa": self._safe_decimal(row.get("roa", row.get("ROA", None))),
                        "revenue_growth": self._safe_decimal(
                            row.get("revenue_growth", row.get("revenueGrowth", None))
                        ),
                        "profit_growth": self._safe_decimal(
                            row.get("profit_growth", row.get("netProfitGrowth", None))
                        ),
                        "current_ratio": self._safe_decimal(
                            row.get("current_ratio", row.get("currentRatio", None))
                        ),
                        "debt_to_equity": self._safe_decimal(
                            row.get("debt_to_equity", row.get("debtToEquity", None))
                        ),
                    },
                )
                await self.session.execute(stmt)
                rows_stored += 1

            except Exception as e:
                logger.warning(f"{symbol} period {idx}: Failed to store — {e}")
                continue

        return rows_stored

    @staticmethod
    def _safe_decimal(value) -> Decimal | None:
        """Convert a value to Decimal, returning None for invalid/missing values."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value) -> int | None:
        """Convert a value to int, returning None for invalid/missing values."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
