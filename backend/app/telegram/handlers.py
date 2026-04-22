"""Telegram bot command handlers.

All commands query the database directly using async_session (same pattern
as scheduler jobs — running outside HTTP request context).
Per CONTEXT.md: single-user, chat_id from settings, Vietnamese responses.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.database import async_session
from app.models.ticker import Ticker
from app.models.daily_price import DailyPrice
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.user_watchlist import UserWatchlist
from app.telegram.formatter import MessageFormatter
from app.services.portfolio_service import PortfolioService


def register_handlers(app: Application) -> None:
    """Register all command handlers with the bot Application."""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("watch", watch_command))
    app.add_handler(CommandHandler("unwatch", unwatch_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("sell", sell_command))
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler("pnl", pnl_command))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — Welcome message with command list."""
    await update.message.reply_text(
        MessageFormatter.welcome(), parse_mode="HTML"
    )


async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/watch <ticker> — Add ticker to watchlist."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            MessageFormatter.usage_error("/watch", "/watch VNM"),
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper().strip()
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        # Look up ticker
        result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol, Ticker.is_active == True)  # noqa: E712
        )
        ticker = result.scalar_one_or_none()
        if not ticker:
            await update.message.reply_text(
                MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
            )
            return

        # Upsert watchlist entry (ON CONFLICT DO NOTHING for idempotency)
        stmt = insert(UserWatchlist).values(
            chat_id=chat_id, ticker_id=ticker.id
        ).on_conflict_do_nothing(
            constraint="uq_user_watchlist_chat_ticker"
        )
        result = await session.execute(stmt)
        await session.commit()

        if result.rowcount > 0:
            await update.message.reply_text(
                MessageFormatter.watch_added(symbol), parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                MessageFormatter.watch_exists(symbol), parse_mode="HTML"
            )


async def unwatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unwatch <ticker> — Remove ticker from watchlist."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            MessageFormatter.usage_error("/unwatch", "/unwatch VNM"),
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper().strip()
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        # Look up ticker
        result = await session.execute(
            select(Ticker.id).where(Ticker.symbol == symbol)
        )
        ticker_id = result.scalar_one_or_none()
        if not ticker_id:
            await update.message.reply_text(
                MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
            )
            return

        # Delete watchlist entry
        result = await session.execute(
            delete(UserWatchlist).where(
                UserWatchlist.chat_id == chat_id,
                UserWatchlist.ticker_id == ticker_id,
            )
        )
        await session.commit()

        if result.rowcount > 0:
            await update.message.reply_text(
                MessageFormatter.watch_removed(symbol), parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                MessageFormatter.watch_not_found(symbol), parse_mode="HTML"
            )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/list — Show all watched tickers with latest signals."""
    chat_id = str(update.effective_chat.id)

    async with async_session() as session:
        # Get all watched tickers
        result = await session.execute(
            select(UserWatchlist.ticker_id, Ticker.symbol)
            .join(Ticker, Ticker.id == UserWatchlist.ticker_id)
            .where(UserWatchlist.chat_id == chat_id)
            .order_by(Ticker.symbol)
        )
        watched = result.all()

        if not watched:
            await update.message.reply_text(
                MessageFormatter.watchlist([]), parse_mode="HTML"
            )
            return

        items = []
        for ticker_id, symbol in watched:
            item = {"symbol": symbol, "signal": None, "score": None, "close": None}

            # Latest combined analysis
            analysis_result = await session.execute(
                select(AIAnalysis.signal, AIAnalysis.score)
                .where(
                    AIAnalysis.ticker_id == ticker_id,
                    AIAnalysis.analysis_type == AnalysisType.COMBINED,
                )
                .order_by(AIAnalysis.analysis_date.desc())
                .limit(1)
            )
            analysis = analysis_result.first()
            if analysis:
                item["signal"] = analysis.signal
                item["score"] = analysis.score

            # Latest close price
            price_result = await session.execute(
                select(DailyPrice.close)
                .where(DailyPrice.ticker_id == ticker_id)
                .order_by(DailyPrice.date.desc())
                .limit(1)
            )
            price = price_result.scalar_one_or_none()
            if price:
                item["close"] = float(price)

            items.append(item)

        await update.message.reply_text(
            MessageFormatter.watchlist(items), parse_mode="HTML"
        )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/check <ticker> — On-demand full analysis summary."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            MessageFormatter.usage_error("/check", "/check VNM"),
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper().strip()

    async with async_session() as session:
        # Look up ticker
        result = await session.execute(
            select(Ticker).where(Ticker.symbol == symbol, Ticker.is_active == True)  # noqa: E712
        )
        ticker = result.scalar_one_or_none()
        if not ticker:
            await update.message.reply_text(
                MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
            )
            return

        data = {"symbol": symbol, "name": ticker.name}

        # Latest price + previous day for change %
        price_result = await session.execute(
            select(DailyPrice.close, DailyPrice.volume, DailyPrice.date)
            .where(DailyPrice.ticker_id == ticker.id)
            .order_by(DailyPrice.date.desc())
            .limit(2)
        )
        prices = price_result.all()
        if prices:
            data["close"] = float(prices[0].close)
            data["volume"] = int(prices[0].volume)
            if len(prices) > 1 and prices[1].close:
                change_pct = ((prices[0].close - prices[1].close) / prices[1].close) * 100
                data["change_pct"] = float(change_pct)

        # All 4 analysis types
        for atype, prefix in [
            (AnalysisType.TECHNICAL, "technical"),
            (AnalysisType.FUNDAMENTAL, "fundamental"),
            (AnalysisType.SENTIMENT, "sentiment"),
            (AnalysisType.COMBINED, "combined"),
        ]:
            a_result = await session.execute(
                select(AIAnalysis.signal, AIAnalysis.score, AIAnalysis.reasoning)
                .where(
                    AIAnalysis.ticker_id == ticker.id,
                    AIAnalysis.analysis_type == atype,
                )
                .order_by(AIAnalysis.analysis_date.desc())
                .limit(1)
            )
            analysis = a_result.first()
            if analysis:
                data[f"{prefix}_signal"] = analysis.signal
                data[f"{prefix}_score"] = analysis.score
                if prefix == "combined":
                    data["combined_reasoning"] = analysis.reasoning

        await update.message.reply_text(
            MessageFormatter.ticker_summary(data), parse_mode="HTML"
        )


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/summary — Force immediate daily summary.

    Uses the same summary generation logic as the scheduled job.
    Imports lazily to avoid circular dependencies (same pattern as scheduler jobs).
    """
    await update.message.reply_text("⏳ Đang tạo tóm tắt...", parse_mode="HTML")

    try:
        from app.telegram.services import AlertService

        async with async_session() as session:
            service = AlertService(session)
            summary_data = await service.build_daily_summary(
                chat_id=str(update.effective_chat.id)
            )

        from app.telegram.bot import telegram_bot

        await telegram_bot.send_message(
            MessageFormatter.daily_summary(summary_data),
            chat_id=str(update.effective_chat.id),
        )
    except Exception as e:
        logger.error(f"Summary command failed: {e}")
        await update.message.reply_text(
            "❌ Không thể tạo tóm tắt. Vui lòng thử lại sau.",
            parse_mode="HTML",
        )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/buy <ticker> <qty> <price> [fee] — Record a buy trade."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            MessageFormatter.usage_error("/buy", "/buy VNM 100 85000"),
            parse_mode="HTML",
        )
        return

    try:
        symbol = context.args[0].upper().strip()
        quantity = int(context.args[1])
        price = float(context.args[2].replace(",", ""))
        fees = float(context.args[3].replace(",", "")) if len(context.args) > 3 else 0
    except (ValueError, IndexError):
        await update.message.reply_text(
            MessageFormatter.usage_error("/buy", "/buy VNM 100 85000"),
            parse_mode="HTML",
        )
        return

    try:
        async with async_session() as session:
            svc = PortfolioService(session)
            result = await svc.record_trade(
                symbol=symbol, side="BUY", quantity=quantity,
                price=price, trade_date=date.today(), fees=fees,
            )
        await update.message.reply_text(
            MessageFormatter.trade_recorded(result), parse_mode="HTML"
        )
    except ValueError as e:
        await update.message.reply_text(
            MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
        )


async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sell <ticker> <qty> <price> [fee] — Record a sell trade."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            MessageFormatter.usage_error("/sell", "/sell VNM 50 90000"),
            parse_mode="HTML",
        )
        return

    try:
        symbol = context.args[0].upper().strip()
        quantity = int(context.args[1])
        price = float(context.args[2].replace(",", ""))
        fees = float(context.args[3].replace(",", "")) if len(context.args) > 3 else 0
    except (ValueError, IndexError):
        await update.message.reply_text(
            MessageFormatter.usage_error("/sell", "/sell VNM 50 90000"),
            parse_mode="HTML",
        )
        return

    try:
        async with async_session() as session:
            svc = PortfolioService(session)
            result = await svc.record_trade(
                symbol=symbol, side="SELL", quantity=quantity,
                price=price, trade_date=date.today(), fees=fees,
            )
        await update.message.reply_text(
            MessageFormatter.trade_recorded(result), parse_mode="HTML"
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            await update.message.reply_text(
                MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"⚠️ {err_msg}", parse_mode="HTML"
            )


async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/portfolio — Show all holdings with P&L."""
    async with async_session() as session:
        svc = PortfolioService(session)
        holdings = await svc.get_holdings()
        summary = await svc.get_summary()
    await update.message.reply_text(
        MessageFormatter.portfolio_view(holdings, summary), parse_mode="HTML"
    )


async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/pnl <ticker> — Detailed P&L with FIFO lot breakdown."""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            MessageFormatter.usage_error("/pnl", "/pnl VNM"),
            parse_mode="HTML",
        )
        return

    symbol = context.args[0].upper().strip()

    try:
        async with async_session() as session:
            svc = PortfolioService(session)
            data = await svc.get_ticker_pnl(symbol)
        await update.message.reply_text(
            MessageFormatter.ticker_pnl(data), parse_mode="HTML"
        )
    except ValueError:
        await update.message.reply_text(
            MessageFormatter.ticker_not_found(symbol), parse_mode="HTML"
        )
