"""Simulator service — paper trading with fee calculation, FIFO matching, portfolio tracking."""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulator_portfolio import SimulatorPortfolio
from app.models.simulator_trade import SimulatorTrade
from app.models.simulator_lot import SimulatorLot
from app.models.ticker import Ticker
from app.models.daily_pick import DailyPick
from app.schemas.simulator import SimulatorTradeCreate

# Fee constants (VN market standard)
BROKER_FEE_PCT = Decimal("0.15")  # 0.15% each side
SELL_TAX_PCT = Decimal("0.1")  # 0.1% sell tax


def calculate_buy_fee(price: Decimal, quantity: int) -> Decimal:
    """Buy fee = 0.15% of transaction value."""
    return (price * quantity * BROKER_FEE_PCT / Decimal("100")).quantize(Decimal("0.01"))


def calculate_sell_fees(price: Decimal, quantity: int) -> tuple[Decimal, Decimal]:
    """Sell fees = 0.15% broker + 0.1% tax."""
    broker = (price * quantity * BROKER_FEE_PCT / Decimal("100")).quantize(Decimal("0.01"))
    tax = (price * quantity * SELL_TAX_PCT / Decimal("100")).quantize(Decimal("0.01"))
    return broker, tax


def fifo_match(lots: list[dict], sell_quantity: int) -> tuple[list[dict], Decimal]:
    """FIFO match sell against oldest lots. Returns matches and gross P&L."""
    matches = []
    remaining = sell_quantity
    total_cost = Decimal("0")

    for lot in sorted(lots, key=lambda x: (x["buy_date"], x["id"])):
        if remaining <= 0:
            break
        take = min(remaining, lot["remaining_quantity"])
        matches.append({"lot_id": lot["id"], "quantity": take, "buy_price": lot["buy_price"]})
        total_cost += lot["buy_price"] * take
        remaining -= take

    if remaining > 0:
        raise ValueError(f"Insufficient lots: need {sell_quantity}, only {sell_quantity - remaining} available")

    return matches, total_cost


class SimulatorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_portfolio(self) -> SimulatorPortfolio:
        """Get default portfolio or create one with 100M VND."""
        result = await self.session.execute(
            select(SimulatorPortfolio).where(SimulatorPortfolio.name == "default")
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            portfolio = SimulatorPortfolio(
                name="default",
                starting_capital=Decimal("100000000"),
                current_cash=Decimal("100000000"),
            )
            self.session.add(portfolio)
            await self.session.flush()
        return portfolio

    async def create_trade(self, data: SimulatorTradeCreate) -> dict:
        """Create a paper trade with auto-calculated fees and FIFO matching."""
        portfolio = await self.get_or_create_portfolio()

        # Resolve ticker
        result = await self.session.execute(
            select(Ticker).where(Ticker.symbol == data.ticker_symbol)
        )
        ticker = result.scalar_one_or_none()
        if not ticker:
            raise ValueError(f"Ticker {data.ticker_symbol} not found")

        price = Decimal(str(data.price))
        quantity = data.quantity

        if data.side == "BUY":
            broker_fee = calculate_buy_fee(price, quantity)
            sell_tax = Decimal("0")
            total_fee = broker_fee
            total_cost = price * quantity + total_fee

            if total_cost > portfolio.current_cash:
                raise ValueError(f"Insufficient cash: need {total_cost}, have {portfolio.current_cash}")

            portfolio.current_cash -= total_cost

            trade = SimulatorTrade(
                portfolio_id=portfolio.id,
                ticker_id=ticker.id,
                daily_pick_id=data.daily_pick_id,
                side="BUY",
                quantity=quantity,
                price=price,
                broker_fee=broker_fee,
                sell_tax=sell_tax,
                total_fee=total_fee,
                trade_date=data.trade_date,
                source=data.source,
                user_notes=data.user_notes,
            )
            self.session.add(trade)
            await self.session.flush()

            # Create lot
            lot = SimulatorLot(
                portfolio_id=portfolio.id,
                ticker_id=ticker.id,
                trade_id=trade.id,
                buy_price=price,
                quantity=quantity,
                remaining_quantity=quantity,
                buy_date=data.trade_date,
            )
            self.session.add(lot)

        else:  # SELL
            broker_fee, sell_tax = calculate_sell_fees(price, quantity)
            total_fee = broker_fee + sell_tax

            # Get open lots for this ticker
            result = await self.session.execute(
                select(SimulatorLot)
                .where(SimulatorLot.portfolio_id == portfolio.id)
                .where(SimulatorLot.ticker_id == ticker.id)
                .where(SimulatorLot.remaining_quantity > 0)
                .order_by(SimulatorLot.buy_date, SimulatorLot.id)
            )
            lots_raw = result.scalars().all()
            lots = [{"id": l.id, "remaining_quantity": l.remaining_quantity, "buy_price": l.buy_price, "buy_date": l.buy_date} for l in lots_raw]

            matches, total_cost = fifo_match(lots, quantity)
            gross_pnl = price * quantity - total_cost
            net_pnl = gross_pnl - total_fee
            proceeds = price * quantity - total_fee

            portfolio.current_cash += proceeds

            trade = SimulatorTrade(
                portfolio_id=portfolio.id,
                ticker_id=ticker.id,
                daily_pick_id=data.daily_pick_id,
                side="SELL",
                quantity=quantity,
                price=price,
                broker_fee=broker_fee,
                sell_tax=sell_tax,
                total_fee=total_fee,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                trade_date=data.trade_date,
                source=data.source,
                user_notes=data.user_notes,
            )
            self.session.add(trade)

            # Deduct from lots
            for match in matches:
                for lot_obj in lots_raw:
                    if lot_obj.id == match["lot_id"]:
                        lot_obj.remaining_quantity -= match["quantity"]
                        break

        await self.session.commit()
        return {
            "id": trade.id,
            "ticker_symbol": ticker.symbol,
            "ticker_name": ticker.name,
            "daily_pick_id": trade.daily_pick_id,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "broker_fee": float(trade.broker_fee),
            "sell_tax": float(trade.sell_tax),
            "total_fee": float(trade.total_fee),
            "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl else None,
            "net_pnl": float(trade.net_pnl) if trade.net_pnl else None,
            "trade_date": str(trade.trade_date),
            "source": trade.source,
            "ai_signal_skipped": trade.ai_signal_skipped,
            "user_notes": trade.user_notes,
            "created_at": str(trade.created_at),
        }

    async def get_portfolio(self) -> dict:
        """Get portfolio state with positions and unrealized P&L."""
        portfolio = await self.get_or_create_portfolio()

        # Get open lots grouped by ticker
        result = await self.session.execute(
            select(
                SimulatorLot.ticker_id,
                func.sum(SimulatorLot.remaining_quantity).label("total_qty"),
                func.sum(SimulatorLot.buy_price * SimulatorLot.remaining_quantity).label("total_cost"),
            )
            .where(SimulatorLot.portfolio_id == portfolio.id)
            .where(SimulatorLot.remaining_quantity > 0)
            .group_by(SimulatorLot.ticker_id)
        )
        positions_raw = result.all()

        positions = []
        total_market_value = Decimal("0")
        total_unrealized = Decimal("0")

        for row in positions_raw:
            ticker_result = await self.session.execute(
                select(Ticker).where(Ticker.id == row.ticker_id)
            )
            ticker = ticker_result.scalar_one()
            qty = int(row.total_qty)
            avg_price = float(row.total_cost / qty) if qty > 0 else 0

            # current_price from latest daily_price (can be None if no data)
            from app.models.daily_price import DailyPrice
            price_result = await self.session.execute(
                select(DailyPrice.close)
                .where(DailyPrice.ticker_id == row.ticker_id)
                .order_by(DailyPrice.date.desc())
                .limit(1)
            )
            current_price_row = price_result.scalar_one_or_none()
            # DailyPrice.close is in nghìn đồng (VCI format), simulator uses VND
            current_price = float(current_price_row) * 1000 if current_price_row else None

            market_value = current_price * qty if current_price else None
            unrealized = (current_price * qty - float(row.total_cost)) if current_price else None

            if market_value:
                total_market_value += Decimal(str(market_value))
            if unrealized:
                total_unrealized += Decimal(str(unrealized))

            positions.append({
                "ticker_symbol": ticker.symbol,
                "ticker_name": ticker.name,
                "quantity": qty,
                "avg_price": round(avg_price, 2),
                "current_price": current_price,
                "market_value": round(market_value, 2) if market_value else None,
                "unrealized_pnl": round(unrealized, 2) if unrealized else None,
                "unrealized_pnl_pct": round(unrealized / float(row.total_cost) * 100, 2) if unrealized and float(row.total_cost) > 0 else None,
            })

        # Realized P&L from sell trades
        realized_result = await self.session.execute(
            select(func.coalesce(func.sum(SimulatorTrade.net_pnl), 0))
            .where(SimulatorTrade.portfolio_id == portfolio.id)
            .where(SimulatorTrade.side == "SELL")
        )
        realized_pnl = float(realized_result.scalar_one())

        total_equity = float(portfolio.current_cash) + float(total_market_value)
        total_pnl = total_equity - float(portfolio.starting_capital)

        return {
            "starting_capital": float(portfolio.starting_capital),
            "current_cash": float(portfolio.current_cash),
            "total_market_value": float(total_market_value),
            "total_equity": round(total_equity, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / float(portfolio.starting_capital) * 100, 2),
            "realized_pnl": realized_pnl,
            "unrealized_pnl": float(total_unrealized),
            "positions": positions,
        }

    async def list_trades(self, page: int = 1, page_size: int = 20, source: str | None = None) -> dict:
        """Get paginated trade history."""
        portfolio = await self.get_or_create_portfolio()
        query = select(SimulatorTrade).where(SimulatorTrade.portfolio_id == portfolio.id)
        count_query = select(func.count(SimulatorTrade.id)).where(SimulatorTrade.portfolio_id == portfolio.id)

        if source:
            query = query.where(SimulatorTrade.source == source)
            count_query = count_query.where(SimulatorTrade.source == source)

        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(
            query.order_by(SimulatorTrade.trade_date.desc(), SimulatorTrade.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        trades = result.scalars().all()

        trade_responses = []
        for t in trades:
            ticker_result = await self.session.execute(select(Ticker).where(Ticker.id == t.ticker_id))
            ticker = ticker_result.scalar_one()
            trade_responses.append({
                "id": t.id,
                "ticker_symbol": ticker.symbol,
                "ticker_name": ticker.name,
                "daily_pick_id": t.daily_pick_id,
                "side": t.side,
                "quantity": t.quantity,
                "price": float(t.price),
                "broker_fee": float(t.broker_fee),
                "sell_tax": float(t.sell_tax),
                "total_fee": float(t.total_fee),
                "gross_pnl": float(t.gross_pnl) if t.gross_pnl else None,
                "net_pnl": float(t.net_pnl) if t.net_pnl else None,
                "trade_date": str(t.trade_date),
                "source": t.source,
                "ai_signal_skipped": t.ai_signal_skipped,
                "user_notes": t.user_notes,
                "created_at": str(t.created_at),
            })

        return {"trades": trade_responses, "total": total, "page": page, "page_size": page_size}

    async def get_stats(self) -> dict:
        """Get AI vs manual performance stats."""
        portfolio = await self.get_or_create_portfolio()

        # All sell trades (have realized P&L)
        result = await self.session.execute(
            select(SimulatorTrade)
            .where(SimulatorTrade.portfolio_id == portfolio.id)
            .where(SimulatorTrade.side == "SELL")
        )
        sell_trades = result.scalars().all()

        ai_sells = [t for t in sell_trades if t.source == "ai_auto"]
        manual_sells = [t for t in sell_trades if t.source == "manual"]

        def calc_stats(trades):
            if not trades:
                return 0.0, 0.0, 0.0
            wins = sum(1 for t in trades if t.net_pnl and t.net_pnl > 0)
            win_rate = wins / len(trades) * 100
            total_pnl = sum(float(t.net_pnl or 0) for t in trades)
            # Avg return % = avg(net_pnl / cost_basis) — approximate using price*qty
            returns = []
            for t in trades:
                cost = float(t.price) * t.quantity
                if cost > 0 and t.net_pnl:
                    returns.append(float(t.net_pnl) / cost * 100)
            avg_return = sum(returns) / len(returns) if returns else 0.0
            return win_rate, avg_return, total_pnl

        ai_wr, ai_avg, ai_pnl = calc_stats(ai_sells)
        m_wr, m_avg, m_pnl = calc_stats(manual_sells)

        # Total trade count
        total_result = await self.session.execute(
            select(func.count(SimulatorTrade.id))
            .where(SimulatorTrade.portfolio_id == portfolio.id)
        )
        total_trades = total_result.scalar_one()

        return {
            "total_trades": total_trades,
            "ai_trades": len([t for t in sell_trades if t.source == "ai_auto"]) * 2,  # approx buy+sell
            "manual_trades": len([t for t in sell_trades if t.source == "manual"]) * 2,
            "ai_win_rate": round(ai_wr, 1),
            "manual_win_rate": round(m_wr, 1),
            "ai_avg_return_pct": round(ai_avg, 2),
            "manual_avg_return_pct": round(m_avg, 2),
            "ai_total_pnl": round(ai_pnl, 2),
            "manual_total_pnl": round(m_pnl, 2),
        }

    async def reset_portfolio(self) -> dict:
        """Reset portfolio to starting state — delete all trades and lots."""
        portfolio = await self.get_or_create_portfolio()
        await self.session.execute(delete(SimulatorLot).where(SimulatorLot.portfolio_id == portfolio.id))
        await self.session.execute(delete(SimulatorTrade).where(SimulatorTrade.portfolio_id == portfolio.id))
        portfolio.current_cash = portfolio.starting_capital
        await self.session.commit()
        return {
            "message": "Portfolio reset to starting capital",
            "starting_capital": float(portfolio.starting_capital),
            "current_cash": float(portfolio.current_cash),
        }
