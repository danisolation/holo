"""Trade journal service.

Pure computation functions for FIFO lot matching, fee calculation, and P&L.
TradeService class handles async DB operations for trade CRUD.

Pure functions are module-level for easy unit testing without DB.
"""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lot import Lot
from app.models.lot_match import LotMatch
from app.models.ticker import Ticker
from app.models.trade import Trade
from app.models.user_risk_profile import UserRiskProfile
from app.schemas.trades import TradeCreate


# ── Pure computation functions ───────────────────────────────────────────────


def calculate_broker_fee(price: Decimal, quantity: int, broker_fee_pct: Decimal) -> Decimal:
    """Broker fee = price × quantity × broker_fee_pct / 100, quantized to 0.01.

    Args:
        price: Trade price per share (VND).
        quantity: Number of shares.
        broker_fee_pct: Broker fee percentage (e.g. 0.150 for 0.15%).

    Returns:
        Fee amount quantized to 2 decimal places.
    """
    return (price * quantity * broker_fee_pct / Decimal("100")).quantize(Decimal("0.01"))


def calculate_sell_tax(price: Decimal, quantity: int) -> Decimal:
    """VN mandatory sell tax = 0.1% of transaction value.

    Args:
        price: Sell price per share (VND).
        quantity: Number of shares sold.

    Returns:
        Tax amount quantized to 2 decimal places.
    """
    return (price * quantity * Decimal("0.001")).quantize(Decimal("0.01"))


def fifo_match_lots(lots: list[dict], sell_quantity: int) -> list[dict]:
    """FIFO: consume oldest lots first.

    Input lots must be pre-sorted by buy_date ASC, id ASC.

    Args:
        lots: List of lot dicts with keys: id, remaining_quantity, buy_price.
        sell_quantity: Number of shares to sell.

    Returns:
        List of matched allocations: [{lot_id, buy_price, matched_quantity}].

    Raises:
        ValueError: If available lots cannot cover sell_quantity.
    """
    remaining = sell_quantity
    matches = []
    for lot in lots:
        if remaining <= 0:
            break
        match_qty = min(lot["remaining_quantity"], remaining)
        matches.append({
            "lot_id": lot["id"],
            "buy_price": lot["buy_price"],
            "matched_quantity": match_qty,
        })
        remaining -= match_qty
    if remaining > 0:
        available = sell_quantity - remaining
        raise ValueError(f"Insufficient lots: need {sell_quantity}, available {available}")
    return matches


def calculate_realized_pnl(
    sell_price: Decimal,
    matches: list[dict],
    sell_broker_fee: Decimal,
    sell_tax: Decimal,
    buy_broker_fees: Decimal,
) -> tuple[Decimal, Decimal]:
    """Calculate realized P&L from matched lot allocations.

    Args:
        sell_price: Sell price per share.
        matches: List of matched lot allocations with buy_price and matched_quantity.
        sell_broker_fee: Total broker fee on the sell side.
        sell_tax: VN mandatory sell tax.
        buy_broker_fees: Total proportional broker fees from buy-side lots.

    Returns:
        Tuple of (gross_pnl, net_pnl).
        gross_pnl = Σ((sell_price - buy_price) × matched_qty)
        net_pnl = gross_pnl - sell_broker_fee - sell_tax - buy_broker_fees
    """
    gross = sum(
        (sell_price - Decimal(str(m["buy_price"]))) * m["matched_quantity"]
        for m in matches
    )
    net = gross - sell_broker_fee - sell_tax - buy_broker_fees
    return (Decimal(str(gross)), Decimal(str(net)))


# ── TradeService (async DB operations) ───────────────────────────────────────


class TradeService:
    """Async service for trade journal CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _resolve_ticker(self, symbol: str) -> tuple[int, str, str]:
        """Resolve ticker symbol to (id, symbol, name). Raises ValueError if not found."""
        result = await self.session.execute(
            select(Ticker.id, Ticker.symbol, Ticker.name).where(Ticker.symbol == symbol.upper())
        )
        row = result.one_or_none()
        if row is None:
            raise ValueError(f"Ticker not found: {symbol}")
        return row.id, row.symbol, row.name

    async def _get_broker_fee_pct(self) -> Decimal:
        """Get broker fee percentage from user risk profile (or default 0.150)."""
        result = await self.session.execute(
            select(UserRiskProfile.broker_fee_pct).limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row is not None else Decimal("0.150")

    async def _get_open_lots(self, ticker_id: int) -> list[dict]:
        """Get open lots for a ticker, sorted for FIFO (buy_date ASC, id ASC)."""
        result = await self.session.execute(
            select(Lot)
            .where(Lot.ticker_id == ticker_id, Lot.remaining_quantity > 0)
            .order_by(Lot.buy_date.asc(), Lot.id.asc())
        )
        lots = result.scalars().all()
        return [
            {
                "id": lot.id,
                "remaining_quantity": lot.remaining_quantity,
                "buy_price": lot.buy_price,
                "trade_id": lot.trade_id,
            }
            for lot in lots
        ]

    async def create_trade(self, data: TradeCreate) -> dict:
        """Create a trade with auto-calculated fees and FIFO matching for SELL.

        Returns dict matching TradeResponse schema fields.
        """
        # 1. Resolve ticker
        ticker_id, ticker_symbol, ticker_name = await self._resolve_ticker(data.ticker_symbol)

        # 2. Get broker fee percentage
        broker_fee_pct = await self._get_broker_fee_pct()

        price = Decimal(str(data.price))
        quantity = data.quantity

        # 3. Calculate fees
        if data.broker_fee_override is not None:
            broker_fee = Decimal(str(data.broker_fee_override))
        else:
            broker_fee = calculate_broker_fee(price, quantity, broker_fee_pct)

        if data.side == "SELL":
            if data.sell_tax_override is not None:
                sell_tax = Decimal(str(data.sell_tax_override))
            else:
                sell_tax = calculate_sell_tax(price, quantity)
        else:
            sell_tax = Decimal("0")

        total_fee = broker_fee + sell_tax

        # 4. FIFO matching for SELL
        gross_pnl = None
        net_pnl = None
        matches = []

        if data.side == "SELL":
            open_lots = await self._get_open_lots(ticker_id)
            matches = fifo_match_lots(open_lots, quantity)

            # Calculate proportional buy-side broker fees
            buy_broker_fees = Decimal("0")
            for m in matches:
                # Find the buy trade's broker_fee for proportional allocation
                lot_info = next(l for l in open_lots if l["id"] == m["lot_id"])
                buy_trade_result = await self.session.execute(
                    select(Trade.broker_fee, Trade.quantity).where(Trade.id == lot_info["trade_id"])
                )
                buy_trade = buy_trade_result.one()
                # Proportional: buy_broker_fee × matched_qty / buy_trade.quantity
                proportional_fee = (buy_trade.broker_fee * m["matched_quantity"] / buy_trade.quantity).quantize(Decimal("0.01"))
                buy_broker_fees += proportional_fee

            gross_pnl, net_pnl = calculate_realized_pnl(
                sell_price=price,
                matches=matches,
                sell_broker_fee=broker_fee,
                sell_tax=sell_tax,
                buy_broker_fees=buy_broker_fees,
            )

        # 5. Create trade record
        trade = Trade(
            ticker_id=ticker_id,
            daily_pick_id=data.daily_pick_id,
            side=data.side,
            quantity=quantity,
            price=price,
            broker_fee=broker_fee,
            sell_tax=sell_tax,
            total_fee=total_fee,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            trade_date=data.trade_date,
            user_notes=data.user_notes,
        )
        self.session.add(trade)
        await self.session.flush()  # Get trade.id

        # 6. If BUY: create lot record
        if data.side == "BUY":
            lot = Lot(
                trade_id=trade.id,
                ticker_id=ticker_id,
                buy_price=price,
                quantity=quantity,
                remaining_quantity=quantity,
                buy_date=data.trade_date,
            )
            self.session.add(lot)

        # 7. If SELL: update lot remaining_quantities, create LotMatch records
        if data.side == "SELL":
            for m in matches:
                # Update lot remaining_quantity
                lot_result = await self.session.execute(
                    select(Lot).where(Lot.id == m["lot_id"])
                )
                lot = lot_result.scalar_one()
                lot.remaining_quantity -= m["matched_quantity"]

                # Create lot match record
                lot_match = LotMatch(
                    sell_trade_id=trade.id,
                    lot_id=m["lot_id"],
                    matched_quantity=m["matched_quantity"],
                )
                self.session.add(lot_match)

        await self.session.commit()
        await self.session.refresh(trade)

        return {
            "id": trade.id,
            "ticker_symbol": ticker_symbol,
            "ticker_name": ticker_name,
            "daily_pick_id": trade.daily_pick_id,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "broker_fee": float(trade.broker_fee),
            "sell_tax": float(trade.sell_tax),
            "total_fee": float(trade.total_fee),
            "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl is not None else None,
            "net_pnl": float(trade.net_pnl) if trade.net_pnl is not None else None,
            "trade_date": str(trade.trade_date),
            "user_notes": trade.user_notes,
            "created_at": trade.created_at.isoformat() if trade.created_at else "",
        }

    async def list_trades(
        self,
        page: int = 1,
        page_size: int = 20,
        ticker: str | None = None,
        side: str | None = None,
        sort: str = "trade_date",
        order: str = "desc",
    ) -> dict:
        """List trades with pagination, filtering, and sorting.

        Returns dict matching TradesListResponse schema.
        """
        # Whitelist sort columns (T-44-05 mitigation)
        allowed_sorts = {"trade_date": Trade.trade_date, "side": Trade.side, "net_pnl": Trade.net_pnl}
        sort_col = allowed_sorts.get(sort, Trade.trade_date)

        # Whitelist order values (T-44-05 mitigation)
        if order not in ("asc", "desc"):
            order = "desc"

        # Base query: join trades with tickers
        base_query = select(
            Trade,
            Ticker.symbol.label("ticker_symbol"),
            Ticker.name.label("ticker_name"),
        ).join(Ticker, Trade.ticker_id == Ticker.id)

        # Apply filters
        if ticker:
            base_query = base_query.where(Ticker.symbol.ilike(f"%{ticker}%"))
        if side and side.upper() in ("BUY", "SELL"):
            base_query = base_query.where(Trade.side == side.upper())

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sort
        if order == "asc":
            base_query = base_query.order_by(sort_col.asc())
        else:
            base_query = base_query.order_by(sort_col.desc())

        # Pagination
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        result = await self.session.execute(base_query)
        rows = result.all()

        trades = []
        for row in rows:
            trade = row[0]  # Trade object
            trades.append({
                "id": trade.id,
                "ticker_symbol": row.ticker_symbol,
                "ticker_name": row.ticker_name,
                "daily_pick_id": trade.daily_pick_id,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": float(trade.price),
                "broker_fee": float(trade.broker_fee),
                "sell_tax": float(trade.sell_tax),
                "total_fee": float(trade.total_fee),
                "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl is not None else None,
                "net_pnl": float(trade.net_pnl) if trade.net_pnl is not None else None,
                "trade_date": str(trade.trade_date),
                "user_notes": trade.user_notes,
                "created_at": trade.created_at.isoformat() if trade.created_at else "",
            })

        return {
            "trades": trades,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_stats(self) -> dict:
        """Get aggregated trade statistics.

        Returns dict matching TradeStatsResponse schema.
        """
        # Total trades
        total_result = await self.session.execute(
            select(func.count()).select_from(Trade)
        )
        total_trades = total_result.scalar() or 0

        # Realized P&L (from SELL trades only)
        pnl_result = await self.session.execute(
            select(
                func.coalesce(func.sum(Trade.gross_pnl), 0).label("realized_gross_pnl"),
                func.coalesce(func.sum(Trade.net_pnl), 0).label("realized_net_pnl"),
            ).where(Trade.side == "SELL")
        )
        pnl_row = pnl_result.one()

        # Open positions (distinct tickers with remaining lots)
        open_result = await self.session.execute(
            select(func.count(func.distinct(Lot.ticker_id))).where(Lot.remaining_quantity > 0)
        )
        open_positions = open_result.scalar() or 0

        return {
            "total_trades": total_trades,
            "realized_gross_pnl": float(pnl_row.realized_gross_pnl),
            "realized_net_pnl": float(pnl_row.realized_net_pnl),
            "open_positions": open_positions,
        }

    async def get_trade(self, trade_id: int) -> dict | None:
        """Get a single trade by ID with ticker info.

        Returns dict matching TradeResponse schema, or None if not found.
        """
        result = await self.session.execute(
            select(
                Trade,
                Ticker.symbol.label("ticker_symbol"),
                Ticker.name.label("ticker_name"),
            )
            .join(Ticker, Trade.ticker_id == Ticker.id)
            .where(Trade.id == trade_id)
        )
        row = result.one_or_none()
        if row is None:
            return None

        trade = row[0]
        return {
            "id": trade.id,
            "ticker_symbol": row.ticker_symbol,
            "ticker_name": row.ticker_name,
            "daily_pick_id": trade.daily_pick_id,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "broker_fee": float(trade.broker_fee),
            "sell_tax": float(trade.sell_tax),
            "total_fee": float(trade.total_fee),
            "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl is not None else None,
            "net_pnl": float(trade.net_pnl) if trade.net_pnl is not None else None,
            "trade_date": str(trade.trade_date),
            "user_notes": trade.user_notes,
            "created_at": trade.created_at.isoformat() if trade.created_at else "",
        }

    async def delete_trade(self, trade_id: int) -> None:
        """Delete a trade and handle lot reversal.

        For SELL: restore consumed lot quantities via lot_matches.
        For BUY: delete the lot only if unconsumed. Error if partially consumed.

        Raises:
            ValueError: If trade not found, or BUY trade has partially consumed lot.
        """
        # Fetch trade
        result = await self.session.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        if trade is None:
            raise ValueError(f"Trade not found: {trade_id}")

        if trade.side == "SELL":
            # Fetch lot matches for this sell trade
            match_result = await self.session.execute(
                select(LotMatch).where(LotMatch.sell_trade_id == trade_id)
            )
            lot_matches = match_result.scalars().all()

            # Restore lot quantities
            for lm in lot_matches:
                lot_result = await self.session.execute(
                    select(Lot).where(Lot.id == lm.lot_id)
                )
                lot = lot_result.scalar_one()
                lot.remaining_quantity += lm.matched_quantity

            # Delete lot matches
            await self.session.execute(
                delete(LotMatch).where(LotMatch.sell_trade_id == trade_id)
            )

        elif trade.side == "BUY":
            # Find associated lot
            lot_result = await self.session.execute(
                select(Lot).where(Lot.trade_id == trade_id)
            )
            lot = lot_result.scalar_one_or_none()

            if lot is not None:
                if lot.remaining_quantity < lot.quantity:
                    raise ValueError(
                        "Cannot delete — this buy has been partially matched by SELL trades"
                    )
                # Unconsumed lot — delete it
                await self.session.delete(lot)

        # Delete the trade itself
        await self.session.delete(trade)
        await self.session.commit()
        logger.info(f"Deleted trade {trade_id} ({trade.side})")
