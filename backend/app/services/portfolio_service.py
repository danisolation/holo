"""Portfolio service: trade recording, FIFO lot management, P&L computation.

Core business logic for Phase 8 portfolio tracking.
Per D-08-01/02/03/06/07 from CONTEXT.md.
"""
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticker import Ticker
from app.models.trade import Trade
from app.models.lot import Lot
from app.models.daily_price import DailyPrice
from app.models.corporate_event import CorporateEvent


class PortfolioService:
    """Trade recording with FIFO lot tracking and P&L computation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_trade(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        trade_date: date,
        fees: float = 0,
    ) -> dict:
        """Record a BUY or SELL trade.

        BUY creates a Trade + Lot. SELL validates available shares,
        consumes lots FIFO, and computes realized P&L.
        """
        ticker = await self._resolve_ticker(symbol)
        price_dec = Decimal(str(price))
        fees_dec = Decimal(str(fees))

        trade = Trade(
            ticker_id=ticker.id,
            side=side.upper(),
            quantity=quantity,
            price=price_dec,
            fees=fees_dec,
            trade_date=trade_date,
        )
        self.session.add(trade)
        await self.session.flush()

        realized_pnl = None

        if side.upper() == "BUY":
            lot = Lot(
                trade_id=trade.id,
                ticker_id=ticker.id,
                buy_price=price_dec,
                quantity=quantity,
                remaining_quantity=quantity,
                buy_date=trade_date,
            )
            self.session.add(lot)
            logger.info(f"BUY {quantity} {symbol} @ {price} recorded (lot created)")
        else:
            realized_pnl = await self._consume_lots_fifo(
                ticker.id, quantity, price_dec, fees_dec
            )
            logger.info(
                f"SELL {quantity} {symbol} @ {price} recorded "
                f"(realized P&L: {realized_pnl})"
            )

        await self.session.commit()

        return {
            "id": trade.id,
            "symbol": ticker.symbol,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "fees": float(trade.fees),
            "trade_date": trade.trade_date.isoformat(),
            "created_at": trade.created_at.isoformat() if trade.created_at else "",
            "realized_pnl": float(realized_pnl) if realized_pnl is not None else None,
        }

    async def get_holdings(self) -> list[dict]:
        """Get current open positions with unrealized P&L."""
        # Aggregate open lots by ticker
        stmt = (
            select(
                Lot.ticker_id,
                func.sum(Lot.remaining_quantity).label("total_qty"),
                (
                    func.sum(Lot.buy_price * Lot.remaining_quantity)
                    / func.sum(Lot.remaining_quantity)
                ).label("avg_cost"),
                func.sum(Lot.buy_price * Lot.remaining_quantity).label("total_cost"),
            )
            .where(Lot.remaining_quantity > 0)
            .group_by(Lot.ticker_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        holdings = []
        for row in rows:
            ticker_id = row.ticker_id
            total_qty = int(row.total_qty)
            avg_cost = float(row.avg_cost)
            total_cost = float(row.total_cost)

            # Get ticker info
            ticker_result = await self.session.execute(
                select(Ticker).where(Ticker.id == ticker_id)
            )
            ticker = ticker_result.scalar_one_or_none()
            if not ticker:
                continue

            # Get latest close price
            price_result = await self.session.execute(
                select(DailyPrice.close)
                .where(DailyPrice.ticker_id == ticker_id)
                .order_by(DailyPrice.date.desc())
                .limit(1)
            )
            latest_close = price_result.scalar_one_or_none()

            market_price = float(latest_close) if latest_close is not None else None
            market_value = market_price * total_qty if market_price is not None else None
            unrealized_pnl = (
                (market_price - avg_cost) * total_qty
                if market_price is not None
                else None
            )
            unrealized_pnl_pct = (
                round(unrealized_pnl / total_cost * 100, 2)
                if unrealized_pnl is not None and total_cost > 0
                else None
            )

            # Compute dividend income for this ticker
            dividend_income = await self.get_dividend_income(ticker_id)

            holdings.append(
                {
                    "symbol": ticker.symbol,
                    "name": ticker.name,
                    "quantity": total_qty,
                    "avg_cost": round(avg_cost, 2),
                    "market_price": market_price,
                    "market_value": round(market_value, 2) if market_value is not None else None,
                    "total_cost": round(total_cost, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
                    "unrealized_pnl_pct": unrealized_pnl_pct,
                    "dividend_income": dividend_income,
                    "sector": ticker.sector,
                }
            )

        return holdings

    async def get_summary(self) -> dict:
        """Get aggregated portfolio summary."""
        # Total invested: sum of price * quantity for all BUY trades
        buy_stmt = select(
            func.coalesce(func.sum(Trade.price * Trade.quantity), 0)
        ).where(Trade.side == "BUY")
        buy_result = await self.session.execute(buy_stmt)
        total_invested = float(buy_result.scalar_one())

        # Realized P&L: sell revenue - cost of sold shares - sell fees
        sell_revenue_stmt = select(
            func.coalesce(func.sum(Trade.price * Trade.quantity), 0)
        ).where(Trade.side == "SELL")
        sell_revenue_result = await self.session.execute(sell_revenue_stmt)
        sell_revenue = sell_revenue_result.scalar_one()

        sell_fees_stmt = select(
            func.coalesce(func.sum(Trade.fees), 0)
        ).where(Trade.side == "SELL")
        sell_fees_result = await self.session.execute(sell_fees_stmt)
        sell_fees = sell_fees_result.scalar_one()

        # Cost of consumed lots = buy_price * (quantity - remaining_quantity) for all lots
        consumed_cost_stmt = select(
            func.coalesce(
                func.sum(Lot.buy_price * (Lot.quantity - Lot.remaining_quantity)), 0
            )
        )
        consumed_cost_result = await self.session.execute(consumed_cost_stmt)
        consumed_cost = consumed_cost_result.scalar_one()

        total_realized_pnl = float(sell_revenue - consumed_cost - sell_fees)

        # Get holdings for unrealized P&L and market value
        holdings = await self.get_holdings()
        total_market_value = None
        total_unrealized_pnl = None

        if holdings:
            mv_values = [h["market_value"] for h in holdings if h["market_value"] is not None]
            upnl_values = [h["unrealized_pnl"] for h in holdings if h["unrealized_pnl"] is not None]

            if mv_values:
                total_market_value = round(sum(mv_values), 2)
            if upnl_values:
                total_unrealized_pnl = round(sum(upnl_values), 2)

        total_return_pct = None
        if total_invested > 0 and total_unrealized_pnl is not None:
            total_return_pct = round(
                (total_realized_pnl + total_unrealized_pnl) / total_invested * 100, 2
            )

        holdings_count = len(holdings)

        # Aggregate dividend income from holdings
        dividend_income = sum(
            h.get("dividend_income", 0) for h in holdings
        )

        return {
            "total_invested": round(total_invested, 2),
            "total_market_value": total_market_value,
            "total_realized_pnl": round(total_realized_pnl, 2),
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_return_pct": total_return_pct,
            "holdings_count": holdings_count,
            "dividend_income": round(dividend_income, 2),
        }

    async def get_dividend_income(self, ticker_id: int) -> float:
        """Compute total dividend income for a ticker from CASH_DIVIDEND events.

        Per PORT-08: sum of dividend_amount × quantity held on record_date.
        Uses historical position: for each dividend event, computes shares held
        on the record_date by checking lots bought before/on record_date, then
        FIFO-deducting shares sold before/on record_date.
        """
        # Query CASH_DIVIDEND events for this ticker with a valid record_date
        events_stmt = (
            select(CorporateEvent)
            .where(
                CorporateEvent.ticker_id == ticker_id,
                CorporateEvent.event_type == "CASH_DIVIDEND",
                CorporateEvent.record_date.isnot(None),
            )
        )
        events_result = await self.session.execute(events_stmt)
        events = events_result.scalars().all()

        if not events:
            return 0.0

        total_income = Decimal("0")

        for event in events:
            # Find ALL lots bought on or before record_date (regardless of current remaining)
            lots_stmt = (
                select(Lot)
                .where(
                    Lot.ticker_id == ticker_id,
                    Lot.buy_date <= event.record_date,
                )
            )
            lots_result = await self.session.execute(lots_stmt)
            lots = lots_result.scalars().all()

            # Compute total sold on or before record_date for this ticker
            sold_before_stmt = (
                select(func.coalesce(func.sum(Trade.quantity), 0))
                .where(
                    Trade.ticker_id == ticker_id,
                    Trade.side == "SELL",
                    Trade.trade_date <= event.record_date,
                )
            )
            sold_result = await self.session.execute(sold_before_stmt)
            total_sold_before = int(sold_result.scalar_one())

            # FIFO: deduct sold shares from oldest lots first
            remaining_sold = total_sold_before
            for lot in sorted(lots, key=lambda l: (l.buy_date, l.id)):
                held = lot.quantity  # original buy quantity
                consumed = min(held, remaining_sold)
                held_on_record = held - consumed
                remaining_sold -= consumed
                total_income += event.dividend_amount * held_on_record

        return float(total_income)

    async def get_performance_data(self, period: str = "3M") -> list[dict]:
        """Compute daily portfolio value snapshots for performance chart.

        Per PORT-09: replay trades chronologically against daily prices.
        Period: 1M→30d, 3M→90d, 6M→180d, 1Y→365d, ALL→earliest trade.
        T-13-01 mitigation: bounded period param, single bulk price query.
        """
        # Compute start_date from period
        period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}
        today = date.today()

        # Fetch all trades ordered by trade_date ASC
        trades_stmt = select(Trade).order_by(Trade.trade_date.asc(), Trade.id.asc())
        trades_result = await self.session.execute(trades_stmt)
        trades = trades_result.scalars().all()

        if not trades:
            return []

        if period == "ALL":
            start_date = trades[0].trade_date
        else:
            days = period_days.get(period, 90)
            start_date = today - timedelta(days=days)

        # Get unique ticker_ids from trades
        ticker_ids = list({t.ticker_id for t in trades})

        # Bulk-fetch daily prices for all held tickers in date range
        prices_stmt = (
            select(DailyPrice)
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= start_date,
            )
            .order_by(DailyPrice.date.asc())
        )
        prices_result = await self.session.execute(prices_stmt)
        price_rows = prices_result.all()

        # Build price lookup: (ticker_id, date) → close
        price_lookup: dict[tuple[int, date], Decimal] = {}
        all_dates: set[date] = set()
        for row in price_rows:
            # Handle both ORM objects and Row tuples
            if hasattr(row, "ticker_id"):
                p = row
            else:
                p = row[0] if len(row) == 1 else row
            price_lookup[(p.ticker_id, p.date)] = p.close
            all_dates.add(p.date)

        if not all_dates:
            return []

        sorted_dates = sorted(all_dates)

        # Build trade lookup by date: date → list of trades on that date
        trades_by_date: dict[date, list] = {}
        for t in trades:
            trades_by_date.setdefault(t.trade_date, []).append(t)

        # Replay positions chronologically
        positions: dict[int, int] = {}  # ticker_id → quantity held
        result = []

        for d in sorted_dates:
            # Apply trades that happened on or before this date
            # (need to apply all trades up to and including this date)
            for trade_date in sorted(trades_by_date.keys()):
                if trade_date > d:
                    break
                for t in trades_by_date[trade_date]:
                    if t.side == "BUY":
                        positions[t.ticker_id] = positions.get(t.ticker_id, 0) + t.quantity
                    else:
                        positions[t.ticker_id] = positions.get(t.ticker_id, 0) - t.quantity
                # Remove processed trades to avoid double-counting
                del trades_by_date[trade_date]

            # Compute total portfolio value for this date
            total_value = Decimal("0")
            has_position = False
            for tid, qty in positions.items():
                if qty > 0:
                    close = price_lookup.get((tid, d))
                    if close is not None:
                        total_value += close * qty
                        has_position = True

            if has_position:
                result.append({
                    "date": d.isoformat(),
                    "value": round(float(total_value), 2),
                })

        return result

    async def get_allocation_data(self, mode: str = "ticker") -> list[dict]:
        """Compute portfolio allocation by ticker or sector.

        Per PORT-10: group holdings by ticker or sector with percentages.
        """
        holdings = await self.get_holdings()

        # Filter holdings with valid market_value
        valid_holdings = [h for h in holdings if h.get("market_value") is not None]
        if not valid_holdings:
            return []

        total_value = sum(h["market_value"] for h in valid_holdings)
        if total_value == 0:
            return []

        if mode == "sector":
            # Group by sector
            sector_values: dict[str, float] = {}
            for h in valid_holdings:
                sector = h.get("sector") or "Khác"
                sector_values[sector] = sector_values.get(sector, 0) + h["market_value"]

            items = [
                {
                    "name": sector,
                    "value": value,
                    "percentage": round(value / total_value * 100, 2),
                }
                for sector, value in sector_values.items()
            ]
        else:
            # Per ticker
            items = [
                {
                    "name": h["symbol"],
                    "value": h["market_value"],
                    "percentage": round(h["market_value"] / total_value * 100, 2),
                }
                for h in valid_holdings
            ]

        # Sort by value descending
        items.sort(key=lambda x: x["value"], reverse=True)
        return items

    async def get_trades(
        self,
        ticker_symbol: str | None = None,
        side: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Get trade history with optional filtering and pagination."""
        base = select(Trade, Ticker.symbol).join(
            Ticker, Trade.ticker_id == Ticker.id
        )

        if ticker_symbol:
            base = base.where(Ticker.symbol == ticker_symbol.upper())
        if side:
            base = base.where(Trade.side == side.upper())

        # Total count
        from sqlalchemy import func as sqlfunc

        count_stmt = select(sqlfunc.count()).select_from(base.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # Paginated results
        data_stmt = base.order_by(
            Trade.trade_date.desc(), Trade.id.desc()
        ).limit(limit).offset(offset)

        result = await self.session.execute(data_stmt)
        rows = result.all()

        trades = []
        for trade, symbol in rows:
            trades.append(
                {
                    "id": trade.id,
                    "symbol": symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": float(trade.price),
                    "fees": float(trade.fees),
                    "trade_date": trade.trade_date.isoformat(),
                    "created_at": trade.created_at.isoformat() if trade.created_at else "",
                    "realized_pnl": None,
                }
            )

        return {"trades": trades, "total": total}

    async def get_ticker_pnl(self, symbol: str) -> dict:
        """Get detailed P&L for a single ticker with FIFO lot breakdown."""
        ticker = await self._resolve_ticker(symbol)

        # Open lots ordered FIFO
        lot_result = await self.session.execute(
            select(Lot)
            .where(Lot.ticker_id == ticker.id, Lot.remaining_quantity > 0)
            .order_by(Lot.buy_date.asc(), Lot.id.asc())
        )
        lots = lot_result.scalars().all()

        # Latest market price
        price_result = await self.session.execute(
            select(DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker.id)
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        latest_close = price_result.scalar_one_or_none()
        market_price = float(latest_close) if latest_close is not None else None

        # Build lot breakdown
        lot_details = []
        total_remaining = 0
        total_cost = Decimal("0")
        total_unrealized = Decimal("0") if market_price is not None else None

        for lot in lots:
            remaining = lot.remaining_quantity
            buy_price = float(lot.buy_price)
            total_remaining += remaining
            total_cost += lot.buy_price * remaining

            lot_pnl = None
            lot_pnl_pct = None
            if market_price is not None:
                lot_pnl = (market_price - buy_price) * remaining
                lot_pnl_pct = round((market_price - buy_price) / buy_price * 100, 2) if buy_price > 0 else None
                total_unrealized += Decimal(str(lot_pnl))

            lot_details.append({
                "buy_date": lot.buy_date.isoformat(),
                "buy_price": buy_price,
                "quantity": lot.quantity,
                "remaining": remaining,
                "lot_pnl": round(lot_pnl, 2) if lot_pnl is not None else None,
                "lot_pnl_pct": lot_pnl_pct,
            })

        avg_cost = float(total_cost / total_remaining) if total_remaining > 0 else 0
        unrealized_pnl = float(total_unrealized) if total_unrealized is not None else None
        unrealized_pnl_pct = (
            round((unrealized_pnl / float(total_cost)) * 100, 2)
            if unrealized_pnl is not None and total_cost > 0
            else None
        )

        # Realized P&L: sell revenue - consumed cost - sell fees
        sell_revenue_stmt = select(
            func.coalesce(func.sum(Trade.price * Trade.quantity), 0)
        ).where(Trade.ticker_id == ticker.id, Trade.side == "SELL")
        sell_revenue_result = await self.session.execute(sell_revenue_stmt)
        sell_revenue = sell_revenue_result.scalar_one()

        sell_fees_stmt = select(
            func.coalesce(func.sum(Trade.fees), 0)
        ).where(Trade.ticker_id == ticker.id, Trade.side == "SELL")
        sell_fees_result = await self.session.execute(sell_fees_stmt)
        sell_fees = sell_fees_result.scalar_one()

        consumed_cost_stmt = select(
            func.coalesce(
                func.sum(Lot.buy_price * (Lot.quantity - Lot.remaining_quantity)), 0
            )
        ).where(Lot.ticker_id == ticker.id)
        consumed_cost_result = await self.session.execute(consumed_cost_stmt)
        consumed_cost = consumed_cost_result.scalar_one()

        realized_pnl = float(sell_revenue - consumed_cost - sell_fees)

        return {
            "symbol": ticker.symbol,
            "name": ticker.name,
            "quantity": total_remaining,
            "avg_cost": round(avg_cost, 2),
            "market_price": market_price,
            "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "realized_pnl": round(realized_pnl, 2),
            "lots": lot_details,
        }

    # --- Private helpers ---

    async def recalculate_lots(self, ticker_id: int) -> None:
        """Delete all lots for ticker and replay trades to rebuild FIFO state.

        Per PORT-11: ensures lot consistency after trade edit/delete.
        T-13-03 mitigation: if sell qty exceeds available during replay, raises ValueError.
        """
        from sqlalchemy import delete as sa_delete

        # Delete all existing lots for this ticker
        await self.session.execute(
            sa_delete(Lot).where(Lot.ticker_id == ticker_id)
        )

        # Query all trades for this ticker ordered chronologically
        result = await self.session.execute(
            select(Trade)
            .where(Trade.ticker_id == ticker_id)
            .order_by(Trade.trade_date.asc(), Trade.id.asc())
        )
        trades = result.scalars().all()

        # Replay: create lots from BUY trades, consume from SELL trades
        open_lots: list[Lot] = []

        for trade in trades:
            if trade.side == "BUY":
                lot = Lot(
                    trade_id=trade.id,
                    ticker_id=ticker_id,
                    buy_price=trade.price,
                    quantity=trade.quantity,
                    remaining_quantity=trade.quantity,
                    buy_date=trade.trade_date,
                )
                self.session.add(lot)
                open_lots.append(lot)
            else:
                # SELL: consume lots FIFO
                remaining_sell = trade.quantity
                available = sum(l.remaining_quantity for l in open_lots)
                if remaining_sell > available:
                    raise ValueError(
                        f"Cannot sell {remaining_sell} shares — only {available} available during FIFO replay"
                    )
                for lot in open_lots:
                    if remaining_sell <= 0:
                        break
                    consumed = min(lot.remaining_quantity, remaining_sell)
                    lot.remaining_quantity -= consumed
                    remaining_sell -= consumed

        await self.session.flush()

    async def update_trade(
        self,
        trade_id: int,
        side: str,
        quantity: int,
        price: float,
        trade_date: date,
        fees: float = 0,
    ) -> dict:
        """Update an existing trade and recalculate FIFO lots. Per PORT-11."""
        # Query trade by id
        result = await self.session.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        if trade is None:
            raise ValueError(f"Trade {trade_id} not found")

        # Update fields
        trade.side = side.upper()
        trade.quantity = quantity
        trade.price = Decimal(str(price))
        trade.fees = Decimal(str(fees))
        trade.trade_date = trade_date

        # Recalculate lots for this ticker
        await self.recalculate_lots(trade.ticker_id)
        await self.session.commit()

        # Get ticker symbol for response
        ticker_result = await self.session.execute(
            select(Ticker).where(Ticker.id == trade.ticker_id)
        )
        ticker = ticker_result.scalar_one_or_none()

        return {
            "id": trade.id,
            "symbol": ticker.symbol if ticker else "",
            "side": trade.side,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "fees": float(trade.fees),
            "trade_date": trade.trade_date.isoformat(),
            "created_at": trade.created_at.isoformat() if trade.created_at else "",
            "realized_pnl": None,
        }

    async def delete_trade(self, trade_id: int) -> dict:
        """Delete a trade and recalculate FIFO lots. Per PORT-11."""
        # Query trade by id
        result = await self.session.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        if trade is None:
            raise ValueError(f"Trade {trade_id} not found")

        ticker_id = trade.ticker_id
        await self.session.delete(trade)
        await self.session.flush()

        # Recalculate lots for this ticker
        await self.recalculate_lots(ticker_id)
        await self.session.commit()

        return {"deleted": True, "trade_id": trade_id}

    async def _resolve_ticker(self, symbol: str) -> Ticker:
        """Resolve symbol to Ticker object. Raises ValueError if not found."""
        result = await self.session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        if ticker is None:
            raise ValueError(f"Ticker '{symbol}' not found")
        return ticker

    async def _validate_sell(self, ticker_id: int, sell_qty: int) -> None:
        """Validate there are enough shares to sell. Per D-08-06."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(Lot.remaining_quantity), 0)).where(
                Lot.ticker_id == ticker_id, Lot.remaining_quantity > 0
            )
        )
        available = int(result.scalar_one())
        if sell_qty > available:
            raise ValueError(
                f"Cannot sell {sell_qty} shares — only {available} available"
            )

    async def _consume_lots_fifo(
        self,
        ticker_id: int,
        sell_qty: int,
        sell_price: Decimal,
        sell_fees: Decimal,
    ) -> Decimal:
        """Consume lots FIFO (oldest first) and compute realized P&L. Per D-08-03."""
        await self._validate_sell(ticker_id, sell_qty)

        result = await self.session.execute(
            select(Lot)
            .where(Lot.ticker_id == ticker_id, Lot.remaining_quantity > 0)
            .order_by(Lot.buy_date.asc(), Lot.id.asc())
        )
        lots = result.scalars().all()

        remaining_sell = sell_qty
        realized_pnl = Decimal("0")

        for lot in lots:
            if remaining_sell <= 0:
                break
            consumed = min(lot.remaining_quantity, remaining_sell)
            realized_pnl += (sell_price - lot.buy_price) * consumed
            lot.remaining_quantity -= consumed
            remaining_sell -= consumed

        realized_pnl -= sell_fees
        return realized_pnl
