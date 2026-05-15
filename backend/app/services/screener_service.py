"""Screener service — screening, peer comparison, and sector detail.

Computes metrics from DailyPrice + Ticker + Financial tables:
1. Screener — filter/sort/paginate tickers with % changes, P/E, volume
2. Peer Comparison — ranked metrics for all tickers in same sector
3. Sector Detail — all tickers in a sector with 7D/30D performance

Uses Python-side computation for % changes (fetches recent prices,
computes in memory) to avoid heavy LAG CTEs over full price history.
P/E sourced from Financial.pe (latest period per ticker), nullable.
"""
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_price import DailyPrice
from app.models.financial import Financial
from app.models.ticker import Ticker


class ScreenerService:
    """Screen, compare, and detail tickers from DailyPrice/Financial data."""

    # Allowed sort columns for screener
    ALLOWED_SORT_COLUMNS = {
        "volume", "change_1d", "change_7d", "change_30d",
        "pe", "close", "market_cap",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_active_tickers(
        self,
        sector: str | None = None,
        industry: str | None = None,
    ) -> list:
        """Fetch active tickers, optionally filtered by sector/industry.

        Returns list of Ticker ORM objects.
        """
        stmt = select(Ticker).where(Ticker.is_active.is_(True))
        if sector is not None:
            stmt = stmt.where(Ticker.sector == sector)
        if industry is not None:
            stmt = stmt.where(Ticker.industry == industry)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_latest_prices(
        self, ticker_ids: list[int],
    ) -> dict[int, dict]:
        """Get latest price row per ticker.

        Returns {ticker_id: {"close": float, "volume": int, "date": date}}.
        """
        if not ticker_ids:
            return {}

        # Subquery: max date per ticker
        max_date_sub = (
            select(
                DailyPrice.ticker_id,
                func.max(DailyPrice.date).label("max_date"),
            )
            .where(DailyPrice.ticker_id.in_(ticker_ids))
            .group_by(DailyPrice.ticker_id)
            .subquery()
        )

        stmt = (
            select(
                DailyPrice.ticker_id,
                DailyPrice.date,
                DailyPrice.close,
                DailyPrice.volume,
            )
            .join(
                max_date_sub,
                (DailyPrice.ticker_id == max_date_sub.c.ticker_id)
                & (DailyPrice.date == max_date_sub.c.max_date),
            )
        )

        result = await self.session.execute(stmt)
        rows = result.fetchall()
        return {
            row.ticker_id: {
                "close": float(row.close) if row.close is not None else None,
                "volume": int(row.volume) if row.volume is not None else None,
                "date": row.date,
            }
            for row in rows
        }

    async def _get_historical_closes(
        self, ticker_ids: list[int], days_back: int = 35,
    ) -> dict[int, list[tuple[date, float]]]:
        """Get recent price history per ticker for change computation.

        Returns {ticker_id: [(date, close), ...]} sorted by date descending.
        Fetches up to `days_back` calendar days of data.
        """
        if not ticker_ids:
            return {}

        cutoff = date.today() - timedelta(days=days_back)
        stmt = (
            select(
                DailyPrice.ticker_id,
                DailyPrice.date,
                DailyPrice.close,
            )
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= cutoff,
            )
            .order_by(DailyPrice.ticker_id, DailyPrice.date.desc())
        )

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        history: dict[int, list[tuple[date, float]]] = {}
        for row in rows:
            history.setdefault(row.ticker_id, []).append(
                (row.date, float(row.close))
            )
        return history

    async def _get_latest_pe(
        self, ticker_ids: list[int],
    ) -> dict[int, float | None]:
        """Get latest P/E ratio per ticker from Financial table.

        Returns {ticker_id: pe_value_or_None}.
        Uses ORDER BY year DESC, quarter DESC NULLS LAST to find latest period.
        """
        if not ticker_ids:
            return {}

        # Subquery: latest financial record per ticker
        # Use row_number to pick latest period per ticker
        from sqlalchemy import case as sa_case

        quarter_sort = sa_case(
            (Financial.quarter.is_(None), 0),
            else_=Financial.quarter,
        )

        latest_sub = (
            select(
                Financial.ticker_id,
                Financial.pe,
                func.row_number().over(
                    partition_by=Financial.ticker_id,
                    order_by=[Financial.year.desc(), quarter_sort.desc()],
                ).label("rn"),
            )
            .where(Financial.ticker_id.in_(ticker_ids))
            .subquery()
        )

        stmt = (
            select(latest_sub.c.ticker_id, latest_sub.c.pe)
            .where(latest_sub.c.rn == 1)
        )

        result = await self.session.execute(stmt)
        rows = result.fetchall()
        return {
            row.ticker_id: float(row.pe) if row.pe is not None else None
            for row in rows
        }

    @staticmethod
    def _compute_changes(
        history: list[tuple[date, float]] | None,
    ) -> dict[str, float | None]:
        """Compute 1D, 7D, 30D % changes from price history.

        history is sorted date descending: [(latest, ...), (prev, ...), ...]
        1D = latest vs 1 trading day ago (index 1)
        7D = latest vs ~5 trading days ago (index 4-6)
        30D = latest vs ~22 trading days ago (index 19-25)
        """
        if not history or len(history) < 2:
            return {"change_1d": None, "change_7d": None, "change_30d": None}

        latest_close = history[0][1]
        if latest_close == 0:
            return {"change_1d": None, "change_7d": None, "change_30d": None}

        def _pct(idx: int) -> float | None:
            if idx < len(history):
                old = history[idx][1]
                if old and old != 0:
                    return round((latest_close - old) / old * 100, 2)
            return None

        # 1D: 1 trading day back
        change_1d = _pct(1)

        # 7D: ~5 trading days back
        change_7d = _pct(min(5, len(history) - 1))

        # 30D: ~22 trading days back
        change_30d = _pct(min(22, len(history) - 1))

        return {
            "change_1d": change_1d,
            "change_7d": change_7d,
            "change_30d": change_30d,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def screen_tickers(
        self,
        sector: str | None = None,
        industry: str | None = None,
        min_volume: int | None = None,
        max_volume: int | None = None,
        min_change: float | None = None,
        max_change: float | None = None,
        min_pe: float | None = None,
        max_pe: float | None = None,
        sort_by: str = "volume",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Screen tickers with filters, sorting, and pagination.

        Fetches active tickers, enriches with latest price + P/E,
        computes % changes, applies filters, sorts, and paginates.

        Returns dict matching ScreenerResponse schema.
        """
        # Validate sort params
        if sort_by not in self.ALLOWED_SORT_COLUMNS:
            sort_by = "volume"
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        # 1. Fetch tickers
        tickers = await self._get_active_tickers(sector, industry)
        if not tickers:
            return {"items": [], "total": 0, "offset": offset, "limit": limit}

        ticker_ids = [t.id for t in tickers]
        ticker_map = {t.id: t for t in tickers}

        # 2. Fetch prices + P/E in parallel-ish (sequential async)
        latest_prices = await self._get_latest_prices(ticker_ids)
        history = await self._get_historical_closes(ticker_ids)
        pe_map = await self._get_latest_pe(ticker_ids)

        # 3. Build enriched items
        items = []
        for tid, ticker in ticker_map.items():
            price_data = latest_prices.get(tid, {})
            changes = self._compute_changes(history.get(tid))
            pe_val = pe_map.get(tid)

            item = {
                "symbol": ticker.symbol,
                "name": ticker.name,
                "sector": ticker.sector,
                "industry": ticker.industry,
                "close": price_data.get("close"),
                "volume": price_data.get("volume"),
                "change_1d": changes["change_1d"],
                "change_7d": changes["change_7d"],
                "change_30d": changes["change_30d"],
                "pe": pe_val,
                "market_cap": (
                    float(ticker.market_cap)
                    if ticker.market_cap is not None
                    else None
                ),
            }
            items.append(item)

        # 4. Apply post-fetch filters
        if min_volume is not None:
            items = [i for i in items if i["volume"] is not None and i["volume"] >= min_volume]
        if max_volume is not None:
            items = [i for i in items if i["volume"] is not None and i["volume"] <= max_volume]
        if min_change is not None:
            items = [i for i in items if i["change_1d"] is not None and i["change_1d"] >= min_change]
        if max_change is not None:
            items = [i for i in items if i["change_1d"] is not None and i["change_1d"] <= max_change]
        if min_pe is not None:
            items = [i for i in items if i["pe"] is not None and i["pe"] >= min_pe]
        if max_pe is not None:
            items = [i for i in items if i["pe"] is not None and i["pe"] <= max_pe]

        # 5. Sort
        reverse = sort_order == "desc"
        items.sort(
            key=lambda x: (x.get(sort_by) is None, x.get(sort_by) or 0),
            reverse=reverse,
        )

        # 6. Paginate
        total = len(items)
        paginated = items[offset: offset + limit]

        return {
            "items": paginated,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def get_peer_comparison(self, symbol: str) -> dict:
        """Get peer comparison for a ticker — all tickers in same sector.

        Ranks each metric (P/E ascending, others descending).
        Marks the target ticker with is_target=True.

        Args:
            symbol: Ticker symbol to compare against peers.

        Returns:
            dict matching PeerComparisonResponse schema.

        Raises:
            ValueError: If ticker not found or has no sector.
        """
        # Find target ticker
        stmt = select(Ticker).where(
            Ticker.symbol == symbol.upper(),
            Ticker.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        target = result.scalar_one_or_none()

        if target is None:
            raise ValueError(f"Ticker '{symbol}' not found")
        if not target.sector:
            raise ValueError(f"Ticker '{symbol}' has no sector assigned")

        # Get all tickers in same sector
        tickers = await self._get_active_tickers(sector=target.sector)
        ticker_ids = [t.id for t in tickers]
        ticker_map = {t.id: t for t in tickers}

        # Fetch data
        latest_prices = await self._get_latest_prices(ticker_ids)
        history = await self._get_historical_closes(ticker_ids, days_back=5)
        pe_map = await self._get_latest_pe(ticker_ids)

        # Build peer items
        peers = []
        for tid, ticker in ticker_map.items():
            price_data = latest_prices.get(tid, {})
            changes = self._compute_changes(history.get(tid))

            peers.append({
                "symbol": ticker.symbol,
                "name": ticker.name,
                "close": price_data.get("close"),
                "volume": price_data.get("volume"),
                "change_1d": changes["change_1d"],
                "pe": pe_map.get(tid),
                "market_cap": (
                    float(ticker.market_cap)
                    if ticker.market_cap is not None
                    else None
                ),
                "is_target": ticker.symbol == symbol.upper(),
            })

        # Rank metrics
        # P/E: ascending (lower = better rank 1)
        # Volume, change_1d, market_cap: descending (higher = better rank 1)
        def _rank(items: list[dict], key: str, ascending: bool = True) -> None:
            """Assign rank_<key> to each item. None values get rank=None."""
            valid = [(i, item[key]) for i, item in enumerate(items) if item[key] is not None]
            valid.sort(key=lambda x: x[1], reverse=not ascending)
            for rank, (idx, _) in enumerate(valid, 1):
                items[idx][f"rank_{key}"] = rank
            for item in items:
                if f"rank_{key}" not in item:
                    item[f"rank_{key}"] = None

        _rank(peers, "pe", ascending=True)
        _rank(peers, "volume", ascending=False)
        _rank(peers, "change_1d", ascending=False)  # rank_change
        _rank(peers, "market_cap", ascending=False)

        # Rename rank_change_1d -> rank_change
        for p in peers:
            p["rank_change"] = p.pop("rank_change_1d", None)

        return {
            "symbol": symbol.upper(),
            "sector": target.sector,
            "peers": peers,
        }

    async def get_sector_detail(self, sector_name: str) -> dict:
        """Get all tickers in a sector with latest price and 7D/30D performance.

        Args:
            sector_name: Sector name to detail.

        Returns:
            dict matching SectorDetailResponse schema.
        """
        tickers = await self._get_active_tickers(sector=sector_name)
        if not tickers:
            return {
                "sector": sector_name,
                "ticker_count": 0,
                "tickers": [],
            }

        ticker_ids = [t.id for t in tickers]
        ticker_map = {t.id: t for t in tickers}

        latest_prices = await self._get_latest_prices(ticker_ids)
        history = await self._get_historical_closes(ticker_ids)

        items = []
        for tid, ticker in ticker_map.items():
            price_data = latest_prices.get(tid, {})
            changes = self._compute_changes(history.get(tid))

            items.append({
                "symbol": ticker.symbol,
                "name": ticker.name,
                "industry": ticker.industry,
                "close": price_data.get("close"),
                "volume": price_data.get("volume"),
                "change_7d": changes["change_7d"],
                "change_30d": changes["change_30d"],
                "market_cap": (
                    float(ticker.market_cap)
                    if ticker.market_cap is not None
                    else None
                ),
            })

        return {
            "sector": sector_name,
            "ticker_count": len(items),
            "tickers": items,
        }
