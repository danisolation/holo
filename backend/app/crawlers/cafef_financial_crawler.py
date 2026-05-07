"""CafeF financial statement scraper for computing financial ratios.

Fetches income statement + balance sheet from CafeF's public financial report
pages (the only VN stock financial data source still accessible without auth).

Computes: P/E, P/B, EPS, ROE, ROA, revenue growth, profit growth,
current ratio, and debt-to-equity from raw financial statement data.

VCI GraphQL API is WAF-blocked, TCBS API deprecated (404), SSI/Fireant need auth.
CafeF remains the only free, reliable source for VN stock financial data.
"""
import asyncio
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.financial import Financial
from app.models.ticker import Ticker
from app.services.ticker_service import TickerService


# VN par value is 10,000 VND per share
_PAR_VALUE = 10_000


def _parse_vn_number(text: str) -> float | None:
    """Parse Vietnamese number format: dots as thousands separator."""
    if not text or text.strip() in ("", "-", "N/A", "0"):
        return None
    text = text.strip().replace(".", "").replace(",", ".")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _to_decimal(val: float | None) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(round(val, 6)))
    except (InvalidOperation, ValueError):
        return None


class CafeFFinancialCrawler:
    """Scrapes CafeF financial statements and computes ratios."""

    BASE_URL = "https://s.cafef.vn/bao-cao-tai-chinh"

    def __init__(self, session: AsyncSession, delay: float = 2.0):
        self.session = session
        self.delay = delay
        self.ticker_service = TickerService(session)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }

    async def crawl_financials(
        self,
        year: int | None = None,
        quarter: int | None = None,
        symbols: list[str] | None = None,
    ) -> dict:
        """Crawl financial data for all active tickers.

        Args:
            year: Report year (default: current year)
            quarter: Report quarter 1-4 (default: latest)
            symbols: Optional list of symbols to crawl (default: all active)

        Returns:
            {success: int, failed: int, failed_symbols: list[str]}
        """
        if year is None:
            today = date.today()
            year = today.year
            if quarter is None:
                # Current quarter - 1 (financial reports lag by ~1 quarter)
                quarter = max(1, (today.month - 1) // 3)
        elif quarter is None:
            quarter = 4

        ticker_map = await self.ticker_service.get_ticker_id_map()
        if symbols:
            ticker_map = {s: tid for s, tid in ticker_map.items() if s in symbols}

        total = len(ticker_map)
        logger.info(
            f"CafeF financial crawl: {total} tickers, period Q{quarter}/{year}"
        )

        success = 0
        failed = 0
        failed_symbols: list[str] = []

        async with httpx.AsyncClient(
            verify=False, timeout=20.0, headers=self.headers,
            follow_redirects=True,
        ) as client:
            for i, (symbol, ticker_id) in enumerate(ticker_map.items()):
                try:
                    ratios = await self._fetch_and_compute(
                        client, symbol, ticker_id, year, quarter
                    )
                    if ratios:
                        await self._store_ratios(ratios)
                        success += 1
                        if (i + 1) % 50 == 0:
                            logger.info(
                                f"CafeF financial progress: {i+1}/{total} "
                                f"(success={success}, failed={failed})"
                            )
                    else:
                        failed += 1
                        failed_symbols.append(symbol)
                except Exception as e:
                    logger.error(f"{symbol}: CafeF financial error — {e}")
                    failed += 1
                    failed_symbols.append(symbol)

                await asyncio.sleep(self.delay)

        await self.session.commit()
        result = {
            "success": success,
            "failed": failed,
            "failed_symbols": failed_symbols[:20],
        }
        logger.info(f"CafeF financial crawl complete: {result}")
        return result

    async def _fetch_and_compute(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        ticker_id: int,
        year: int,
        quarter: int,
    ) -> dict | None:
        """Fetch income statement + balance sheet, compute ratios."""
        # Fetch income statement
        inc_url = (
            f"{self.BASE_URL}/{symbol}/IncSta/{year}/{quarter}"
            f"/0/0/bao-cao-ket-qua-hoat-dong-kinh-doanh-.chn"
        )
        inc_data = await self._fetch_table_data(client, inc_url)
        if not inc_data:
            logger.warning(f"{symbol}: No income statement data from CafeF")
            return None

        # Fetch balance sheet
        bs_url = (
            f"{self.BASE_URL}/{symbol}/BSheet/{year}/{quarter}"
            f"/0/0/co-cau-tai-san-.chn"
        )
        bs_data = await self._fetch_table_data(client, bs_url)
        if not bs_data:
            logger.warning(f"{symbol}: No balance sheet data from CafeF")
            return None

        # Also get previous period for growth calculations
        prev_year = year if quarter > 1 else year - 1
        prev_quarter = quarter - 1 if quarter > 1 else 4
        prev_inc_url = (
            f"{self.BASE_URL}/{symbol}/IncSta/{prev_year}/{prev_quarter}"
            f"/0/0/bao-cao-ket-qua-hoat-dong-kinh-doanh-.chn"
        )
        prev_inc = await self._fetch_table_data(client, prev_inc_url)

        # Get current price for P/E and P/B calculations
        current_price = await self._get_current_price(ticker_id)

        return self._compute_ratios(
            symbol, ticker_id, year, quarter,
            inc_data, bs_data, prev_inc, current_price
        )

    async def _fetch_table_data(
        self, client: httpx.AsyncClient, url: str
    ) -> dict[str, float | None]:
        """Fetch and parse CafeF financial table page."""
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {}

            soup = BeautifulSoup(resp.text, "html.parser")
            data = {}
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                if len(rows) > 10:
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            name = cells[0].get_text(strip=True)
                            # First data column = current quarter
                            val = cells[1].get_text(strip=True)
                            if name:
                                data[name] = _parse_vn_number(val)
            return data
        except Exception as e:
            logger.debug(f"CafeF fetch error {url}: {e}")
            return {}

    async def _get_current_price(self, ticker_id: int) -> float | None:
        """Get current price from daily_prices table (in nghìn đồng)."""
        from app.models.daily_price import DailyPrice

        result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None

    def _compute_ratios(
        self,
        symbol: str,
        ticker_id: int,
        year: int,
        quarter: int,
        inc: dict,
        bs: dict,
        prev_inc: dict | None,
        current_price: float | None,
    ) -> dict | None:
        """Compute financial ratios from raw statement data."""
        # Extract key values from income statement
        net_profit = self._find_value(inc, [
            "18. L", "nhu\u1eadn sau thu\u1ebf thu nh\u1eadp doanh nghi\u1ec7p",
            "L\u1ee3i nhu\u1eadn sau thu\u1ebf",
        ])
        revenue = self._find_value(inc, [
            "3. Doanh thu thu\u1ea7n",
            "Doanh thu thu\u1ea7n v\u1ec1 b\u00e1n h\u00e0ng",
        ])

        # Extract key values from balance sheet
        total_assets = self._find_value(bs, [
            "T\u1ed4NG C\u1ed8NG T\u00c0I S\u1ea2N",
            "T\u1ed5ng c\u1ed9ng t\u00e0i s\u1ea3n",
        ])
        total_equity = self._find_value(bs, [
            "D.V\u1ed0N CH\u1ee6 S\u1ede H\u1eecu",
            "V\u1ed1n ch\u1ee7 s\u1edf h\u1eefu",
            "I. V\u1ed1n ch\u1ee7 s\u1edf h\u1eefu",
        ])
        total_debt = self._find_value(bs, [
            "C. N\u1ee2 PH\u1ea2I TR\u1ea2",
            "N\u1ee3 ph\u1ea3i tr\u1ea3",
        ])
        share_capital = self._find_value(bs, [
            "1. V\u1ed1n g\u00f3p c\u1ee7a ch\u1ee7 s\u1edf h\u1eefu",
            "V\u1ed1n g\u00f3p",
        ])
        current_assets = self._find_value(bs, [
            "A- T\u00c0I S\u1ea2N NG\u1eaeN H\u1ea0N",
            "A. T\u00e0i s\u1ea3n ng\u1eafn h\u1ea1n",
        ])
        current_liabilities = self._find_value(bs, [
            "I. N\u1ee3 ng\u1eafn h\u1ea1n",
        ])

        if net_profit is None and revenue is None:
            logger.debug(f"{symbol}: Could not extract any financial data")
            return None

        # Compute ratios
        shares_outstanding = None
        if share_capital:
            shares_outstanding = share_capital / _PAR_VALUE

        eps = None
        if net_profit is not None and shares_outstanding:
            eps = net_profit / shares_outstanding

        pe = None
        if current_price and eps and eps > 0:
            # price in nghìn đồng, EPS in full VND → convert price to VND
            pe = (current_price * 1000) / eps

        pb = None
        if current_price and total_equity and shares_outstanding:
            bvps = total_equity / shares_outstanding
            if bvps > 0:
                pb = (current_price * 1000) / bvps

        roe = None
        if net_profit is not None and total_equity and total_equity > 0:
            roe = net_profit / total_equity

        roa = None
        if net_profit is not None and total_assets and total_assets > 0:
            roa = net_profit / total_assets

        debt_to_equity = None
        if total_debt is not None and total_equity and total_equity > 0:
            debt_to_equity = total_debt / total_equity

        current_ratio = None
        if current_assets and current_liabilities and current_liabilities > 0:
            current_ratio = current_assets / current_liabilities

        # Growth rates (vs previous quarter)
        revenue_growth = None
        profit_growth = None
        if prev_inc:
            prev_revenue = self._find_value(prev_inc, [
                "3. Doanh thu thu\u1ea7n",
                "Doanh thu thu\u1ea7n v\u1ec1 b\u00e1n h\u00e0ng",
            ])
            prev_profit = self._find_value(prev_inc, [
                "18. L", "nhu\u1eadn sau thu\u1ebf thu nh\u1eadp doanh nghi\u1ec7p",
            ])
            if prev_revenue and revenue and prev_revenue > 0:
                revenue_growth = (revenue - prev_revenue) / abs(prev_revenue)
            if prev_profit and net_profit is not None and prev_profit != 0:
                profit_growth = (net_profit - prev_profit) / abs(prev_profit)

        period_str = f"Q{quarter}-{year}"

        return {
            "ticker_id": ticker_id,
            "period": period_str,
            "year": year,
            "quarter": quarter,
            "pe": _to_decimal(pe),
            "pb": _to_decimal(pb),
            "eps": _to_decimal(eps),
            "roe": _to_decimal(roe),
            "roa": _to_decimal(roa),
            "revenue_growth": _to_decimal(revenue_growth),
            "profit_growth": _to_decimal(profit_growth),
            "current_ratio": _to_decimal(current_ratio),
            "debt_to_equity": _to_decimal(debt_to_equity),
        }

    def _find_value(
        self, data: dict[str, float | None], patterns: list[str]
    ) -> float | None:
        """Find a value in parsed table data by matching row name patterns."""
        for key, val in data.items():
            for pattern in patterns:
                if pattern.lower() in key.lower():
                    return val
        return None

    async def _store_ratios(self, ratios: dict) -> None:
        """Upsert financial ratios into the financials table."""
        stmt = (
            insert(Financial)
            .values(ratios)
            .on_conflict_do_update(
                constraint="uq_financials_ticker_period",
                set_={
                    "pe": ratios["pe"],
                    "pb": ratios["pb"],
                    "eps": ratios["eps"],
                    "roe": ratios["roe"],
                    "roa": ratios["roa"],
                    "revenue_growth": ratios["revenue_growth"],
                    "profit_growth": ratios["profit_growth"],
                    "current_ratio": ratios["current_ratio"],
                    "debt_to_equity": ratios["debt_to_equity"],
                },
            )
        )
        await self.session.execute(stmt)
