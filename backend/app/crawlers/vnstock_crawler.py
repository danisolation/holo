"""Async wrapper around synchronous vnstock library.

vnstock uses `requests` (synchronous HTTP). All calls MUST go through
asyncio.to_thread() to avoid blocking FastAPI's event loop.
A 13-minute crawl loop would freeze all API endpoints if run synchronously.

NOTE: We use vnstock sub-modules directly (Quote, Listing, Finance) instead
of the Vnstock().stock() factory because VCI's Company API changed and
the factory's Company init now fails with KeyError: 'data'.
"""
import asyncio
import os
import ssl
import pandas as pd

# Workaround: VietCap uses a self-signed cert in their chain.
# Disable SSL verification for vnstock HTTP calls.
os.environ.setdefault("CURL_CA_BUNDLE", "")
os.environ.setdefault("REQUESTS_CA_BUNDLE", "")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkey-patch requests Session to skip SSL verify for VietCap
import requests
_original_send = requests.Session.send

def _patched_send(self, request, **kwargs):
    if "vietcap.com.vn" in (request.url or ""):
        kwargs["verify"] = False
    return _original_send(self, request, **kwargs)

requests.Session.send = _patched_send

from vnstock.explorer.vci.listing import Listing
from vnstock.explorer.vci.quote import Quote
from vnstock.explorer.vci.financial import Finance
from vnstock.explorer.vci.trading import Trading
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from app.config import settings
from app.resilience import vnstock_breaker

# VCI Company API is broken (KeyError: 'data'), so Finance.__init__ fails
# when calling _get_company_type(). Monkey-patch to return com_type_code
# based on known industry classification without calling Company API.
_BANK_SYMBOLS = {
    "ACB", "BID", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
    "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VAB", "VCB",
    "VIB", "VPB", "BAB", "BVB", "KLB", "SGB", "ABB", "NVB", "VBB",
}
_INSURANCE_SYMBOLS = {"BVH", "BMI", "MIG", "PVI", "BIC", "PTI", "VNR", "ABI"}
_SECURITIES_SYMBOLS = {
    "SSI", "VCI", "HCM", "VND", "MBS", "SHS", "VDS", "BSI", "CTS",
    "ORS", "TVS", "AGR", "APG", "APS", "BMS", "BVS", "DIG", "EVS",
    "FTS", "HAC", "IVS", "KIS", "PSI", "TCI", "TVB", "VIG", "WSS",
}

def _patched_get_company_type(self) -> str:
    sym = self.symbol.upper()
    if sym in _BANK_SYMBOLS:
        return "NH"
    if sym in _INSURANCE_SYMBOLS:
        return "BH"
    if sym in _SECURITIES_SYMBOLS:
        return "CK"
    return "CT"

Finance._get_company_type = _patched_get_company_type

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
    async def _fetch_listing_with_retry(self, exchange: str = "HOSE") -> pd.DataFrame:
        """Internal: fetch with tenacity retry. Circuit breaker wraps this."""
        def _fetch():
            listing = Listing()
            df = listing.symbols_by_exchange()
            vci_exchange = _EXCHANGE_MAP.get(exchange, exchange)
            return df.query(f'exchange == "{vci_exchange}" and type == "STOCK"')

        logger.debug(f"Fetching listing for {exchange}")
        return await asyncio.to_thread(_fetch)

    async def fetch_listing(self, exchange: str = "HOSE") -> pd.DataFrame:
        """Fetch all tickers for an exchange.

        Returns DataFrame with columns: symbol, exchange, type,
        organ_name, organ_short_name, ...
        Filters to stocks only (excludes ETFs, bonds).
        Circuit breaker wraps OUTSIDE tenacity retries (Pitfall 1).
        """
        return await vnstock_breaker.call(self._fetch_listing_with_retry, exchange)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def _fetch_ohlcv_with_retry(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Internal: fetch with tenacity retry. Circuit breaker wraps this."""
        def _fetch():
            quote = Quote(symbol)
            return quote.history(start=start, end=end, interval='1D')

        logger.debug(f"Fetching OHLCV for {symbol} from {start} to {end}")
        return await asyncio.to_thread(_fetch)

    async def fetch_ohlcv(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Fetch OHLCV history for one ticker.

        Returns DataFrame with columns: time, open, high, low, close, volume.
        Circuit breaker wraps OUTSIDE tenacity retries (Pitfall 1).
        """
        return await vnstock_breaker.call(self._fetch_ohlcv_with_retry, symbol, start, end)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def _fetch_financial_ratios_with_retry(self, symbol: str, period: str = "quarter") -> pd.DataFrame:
        """Internal: fetch with tenacity retry. Circuit breaker wraps this."""
        def _fetch():
            finance = Finance(symbol)
            return finance.ratio(period=period, lang='en', dropna=True)

        logger.debug(f"Fetching financial ratios for {symbol} ({period})")
        return await asyncio.to_thread(_fetch)

    async def fetch_financial_ratios(self, symbol: str, period: str = "quarter") -> pd.DataFrame:
        """Fetch financial ratios (P/E, P/B, revenue, etc.).

        Returns MultiIndex DataFrame with financial metrics across periods.
        Circuit breaker wraps OUTSIDE tenacity retries (Pitfall 1).
        """
        return await vnstock_breaker.call(self._fetch_financial_ratios_with_retry, symbol, period)

    @retry(
        stop=stop_after_attempt(settings.crawl_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def _fetch_industry_classification_with_retry(self) -> pd.DataFrame:
        """Internal: fetch with tenacity retry. Circuit breaker wraps this."""
        def _fetch():
            listing = Listing()
            return listing.symbols_by_industries()

        logger.debug("Fetching industry classifications")
        return await asyncio.to_thread(_fetch)

    async def fetch_industry_classification(self) -> pd.DataFrame:
        """Fetch ICB industry classification for all tickers.

        Returns DataFrame with: symbol, organ_name, icb_name2 (sector),
        icb_name3, icb_name4, com_type_code.
        Circuit breaker wraps OUTSIDE tenacity retries (Pitfall 1).
        """
        return await vnstock_breaker.call(self._fetch_industry_classification_with_retry)

    async def fetch_price_board(self, symbols: list[str]) -> dict[str, dict]:
        """Fetch current prices for multiple symbols via VCI price_board.

        Uses vnstock Trading module to get real-time price board data.
        Returns dict keyed by symbol: {"VNM": {"price": ..., "change": ..., "change_pct": ..., "volume": ...}}

        No retry/circuit-breaker — this is called frequently (every 30s)
        and transient failures are acceptable for real-time polling.
        """
        if not symbols:
            return {}

        def _fetch():
            trading = Trading(show_log=False)
            df = trading.price_board(symbols_list=symbols)
            result = {}
            for _, row in df.iterrows():
                try:
                    sym = row[("listing", "symbol")]
                    price = row[("match", "match_price")]
                    ref_price = row[("match", "reference_price")]
                    volume = row[("match", "accumulated_volume")]

                    # Skip tickers with NaN/None price data (e.g. suspended tickers)
                    if not pd.notna(price) or not pd.notna(volume):
                        logger.debug(f"Skipping {sym}: NaN price or volume")
                        continue

                    # VCI returns prices in VND; DB convention is nghìn đồng (÷1000)
                    price_k = float(price) / 1000.0
                    ref_k = float(ref_price) / 1000.0 if pd.notna(ref_price) and float(ref_price) > 0 else 0.0

                    change = price_k - ref_k if ref_k > 0 else 0.0
                    change_pct = (change / ref_k * 100) if ref_k > 0 else 0.0

                    result[sym] = {
                        "price": price_k,
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "volume": int(volume),
                    }
                except (ValueError, TypeError, KeyError) as e:
                    # Isolate per-ticker failures so one bad row doesn't crash the batch
                    logger.warning(f"Skipping ticker due to data error: {e}")
                    continue
            return result

        logger.debug(f"Fetching price board for {len(symbols)} symbols")
        return await asyncio.to_thread(_fetch)
