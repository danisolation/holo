"""Async wrapper around synchronous vnstock library.

vnstock uses `requests` (synchronous HTTP). All calls MUST go through
asyncio.to_thread() to avoid blocking FastAPI's event loop.
A 13-minute crawl loop would freeze all API endpoints if run synchronously.

NOTE: We use vnstock sub-modules directly (Quote, Listing, Finance) instead
of the Vnstock().stock() factory because VCI's Company API changed and
the factory's Company init now fails with KeyError: 'data'.
"""
import asyncio
import pandas as pd
from vnstock.explorer.vci.listing import Listing
from vnstock.explorer.vci.quote import Quote
from vnstock.explorer.vci.financial import Finance
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from app.config import settings

# VCI API uses 'HSX' for HOSE exchange
_EXCHANGE_MAP = {"HOSE": "HSX", "HNX": "HNX", "UPCOM": "UPCOM"}


class VnstockCrawler:
    """Async wrapper around synchronous vnstock library."""

    def __init__(self, source: str | None = None):
        self.source = source or settings.vnstock_source

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
            listing = Listing()
            df = listing.symbols_by_exchange()
            vci_exchange = _EXCHANGE_MAP.get(exchange, exchange)
            return df.query(f'exchange == "{vci_exchange}" and type == "STOCK"')

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
            quote = Quote(symbol)
            return quote.history(start=start, end=end, interval='1D')

        logger.debug(f"Fetching OHLCV for {symbol} from {start} to {end}")
        return await asyncio.to_thread(_fetch)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_financial_ratios(self, symbol: str, period: str = "quarter") -> pd.DataFrame:
        """Fetch financial ratios (P/E, P/B, revenue, etc.).

        Returns MultiIndex DataFrame with financial metrics across periods.
        """
        def _fetch():
            finance = Finance(symbol)
            return finance.ratio(period=period, lang='en', dropna=True)

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
            listing = Listing()
            return listing.symbols_by_industries()

        logger.debug("Fetching industry classifications")
        return await asyncio.to_thread(_fetch)
