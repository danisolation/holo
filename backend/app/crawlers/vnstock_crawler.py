"""Async wrapper around synchronous vnstock library.

vnstock uses `requests` (synchronous HTTP). All calls MUST go through
asyncio.to_thread() to avoid blocking FastAPI's event loop.
A 13-minute crawl loop would freeze all API endpoints if run synchronously.
"""
import asyncio
import pandas as pd
from vnstock import Vnstock
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from app.config import settings


class VnstockCrawler:
    """Async wrapper around synchronous vnstock library."""

    def __init__(self, source: str | None = None):
        self.source = source or settings.vnstock_source

    def _create_stock(self, symbol: str):
        """Create a vnstock stock object (sync — called inside to_thread)."""
        return Vnstock(show_log=False).stock(symbol=symbol, source=self.source)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_listing(self, exchange: str = "HOSE") -> pd.DataFrame:
        """Fetch all tickers for an exchange.

        Returns DataFrame with columns: symbol, exchange, type,
        organ_name, organ_short_name, ...
        Filters to stocks only (excludes ETFs, bonds).
        """
        def _fetch():
            stock = self._create_stock("ACB")  # symbol required but arbitrary
            df = stock.listing.symbols_by_exchange()
            return df.query(f'exchange == "{exchange}" and type == "STOCK"')

        logger.debug(f"Fetching listing for {exchange}")
        return await asyncio.to_thread(_fetch)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_ohlcv(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Fetch OHLCV history for one ticker.

        Returns DataFrame with columns: time, open, high, low, close, volume.
        NOTE: No adjusted_close — vnstock returns UNADJUSTED prices only.
        """
        def _fetch():
            stock = self._create_stock(symbol)
            return stock.quote.history(start=start, end=end, interval='1D')

        logger.debug(f"Fetching OHLCV for {symbol} from {start} to {end}")
        return await asyncio.to_thread(_fetch)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_financial_ratios(self, symbol: str, period: str = "quarter") -> pd.DataFrame:
        """Fetch financial ratios (P/E, P/B, revenue, etc.).

        WARNING: Finance.__init__() triggers an extra API call per ticker
        to determine com_type_code. Factor this into rate limiting.

        Returns MultiIndex DataFrame with financial metrics across periods.
        """
        def _fetch():
            stock = self._create_stock(symbol)
            return stock.finance.ratio(period=period, lang='en', dropna=True)

        logger.debug(f"Fetching financial ratios for {symbol} ({period})")
        return await asyncio.to_thread(_fetch)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_industry_classification(self) -> pd.DataFrame:
        """Fetch ICB industry classification for all tickers.

        Returns DataFrame with: symbol, organ_name, icb_name2 (sector),
        icb_name3, icb_name4, com_type_code.
        """
        def _fetch():
            stock = self._create_stock("ACB")
            return stock.listing.symbols_by_industries()

        logger.debug("Fetching industry classifications")
        return await asyncio.to_thread(_fetch)
