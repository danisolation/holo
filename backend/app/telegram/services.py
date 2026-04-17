"""Alert and summary services for Telegram bot.

Handles:
- Signal change detection: compares today's combined signal vs yesterday's for watched tickers
- Price threshold checking: checks active (non-triggered) price alerts vs latest close
- Daily summary: top movers, watchlist changes, new strong recommendations

All methods are stateless — they take a session and return data or send messages.
Telegram send failures are logged but never raised (per CONTEXT.md D-3.4).
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, update, func as sa_func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ticker import Ticker
from app.models.daily_price import DailyPrice
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.user_watchlist import UserWatchlist
from app.models.price_alert import PriceAlert
from app.telegram.formatter import MessageFormatter


class AlertService:
    """Processes alert conditions and builds summary data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_signal_changes(self, chat_id: str | None = None) -> int:
        """Detect signal changes for watched tickers and send alerts.

        Compares today's combined analysis signal vs yesterday's for all tickers
        in the watchlist. Sends a Telegram alert for each change.

        Per CONTEXT.md D-2.1: triggers after combined analysis completes.

        Args:
            chat_id: Target chat ID. Defaults to settings.telegram_chat_id.

        Returns: Number of signal change alerts sent.
        """
        target_chat = chat_id or settings.telegram_chat_id
        if not target_chat:
            logger.warning("No chat_id for signal alerts — skipping")
            return 0

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Get all watched ticker IDs for this chat
        result = await self.session.execute(
            select(UserWatchlist.ticker_id, Ticker.symbol)
            .join(Ticker, Ticker.id == UserWatchlist.ticker_id)
            .where(UserWatchlist.chat_id == target_chat)
        )
        watched = result.all()

        if not watched:
            logger.info("No watched tickers — skipping signal alert check")
            return 0

        alerts_sent = 0
        for ticker_id, symbol in watched:
            # Get today's combined signal
            today_result = await self.session.execute(
                select(AIAnalysis.signal, AIAnalysis.score, AIAnalysis.reasoning)
                .where(
                    AIAnalysis.ticker_id == ticker_id,
                    AIAnalysis.analysis_type == AnalysisType.COMBINED,
                    AIAnalysis.analysis_date == today,
                )
            )
            today_analysis = today_result.first()
            if not today_analysis:
                continue

            # Get yesterday's combined signal
            yesterday_result = await self.session.execute(
                select(AIAnalysis.signal)
                .where(
                    AIAnalysis.ticker_id == ticker_id,
                    AIAnalysis.analysis_type == AnalysisType.COMBINED,
                    AIAnalysis.analysis_date == yesterday,
                )
            )
            yesterday_analysis = yesterday_result.first()

            # Alert on change (or if first day with analysis)
            old_signal = yesterday_analysis.signal if yesterday_analysis else None
            new_signal = today_analysis.signal

            if old_signal and old_signal != new_signal:
                msg = MessageFormatter.signal_change(
                    symbol=symbol,
                    old_signal=old_signal,
                    new_signal=new_signal,
                    score=today_analysis.score,
                    reasoning=today_analysis.reasoning or "",
                )
                # Lazy import to avoid circular dependency
                from app.telegram.bot import telegram_bot
                sent = await telegram_bot.send_message(msg, chat_id=target_chat)
                if sent:
                    alerts_sent += 1

        logger.info(f"Signal alert check complete: {alerts_sent} alerts sent for {len(watched)} watched tickers")
        return alerts_sent

    async def check_price_alerts(self, chat_id: str | None = None) -> int:
        """Check active price alerts against latest close prices.

        For each non-triggered alert:
        - direction="up": alert if latest close >= target_price
        - direction="down": alert if latest close <= target_price
        Triggered alerts are marked is_triggered=True with triggered_at timestamp.

        Per CONTEXT.md D-2.2: triggers after daily price crawl.

        Args:
            chat_id: Target chat ID. Defaults to settings.telegram_chat_id.

        Returns: Number of price alerts triggered.
        """
        target_chat = chat_id or settings.telegram_chat_id
        if not target_chat:
            logger.warning("No chat_id for price alerts — skipping")
            return 0

        # Get all active (non-triggered) alerts for this chat
        result = await self.session.execute(
            select(PriceAlert, Ticker.symbol)
            .join(Ticker, Ticker.id == PriceAlert.ticker_id)
            .where(
                PriceAlert.chat_id == target_chat,
                PriceAlert.is_triggered == False,  # noqa: E712
            )
        )
        active_alerts = result.all()

        if not active_alerts:
            logger.info("No active price alerts — skipping")
            return 0

        triggered_count = 0
        for alert, symbol in active_alerts:
            # Get latest close price
            price_result = await self.session.execute(
                select(DailyPrice.close)
                .where(DailyPrice.ticker_id == alert.ticker_id)
                .order_by(DailyPrice.date.desc())
                .limit(1)
            )
            latest_close = price_result.scalar_one_or_none()
            if latest_close is None:
                continue

            # Check threshold
            crossed = False
            if alert.direction == "up" and latest_close >= alert.target_price:
                crossed = True
            elif alert.direction == "down" and latest_close <= alert.target_price:
                crossed = True

            if crossed:
                # Mark as triggered
                await self.session.execute(
                    update(PriceAlert)
                    .where(PriceAlert.id == alert.id)
                    .values(is_triggered=True, triggered_at=datetime.now(timezone.utc))
                )
                await self.session.commit()

                # Send notification
                msg = MessageFormatter.alert_triggered(
                    symbol=symbol,
                    current_price=latest_close,
                    target_price=alert.target_price,
                    direction=alert.direction,
                )
                from app.telegram.bot import telegram_bot
                sent = await telegram_bot.send_message(msg, chat_id=target_chat)
                if sent:
                    triggered_count += 1

        logger.info(f"Price alert check complete: {triggered_count} alerts triggered from {len(active_alerts)} active")
        return triggered_count

    async def build_daily_summary(self, chat_id: str | None = None) -> dict:
        """Build daily summary data dict for formatting.

        Includes:
        - Top 5 movers by absolute price change %
        - Signal changes for watchlist tickers
        - New strong recommendations (mua with confidence >= 7)

        Per CONTEXT.md D-2.3: scheduled at 16:00 UTC+7.

        Returns: dict suitable for MessageFormatter.daily_summary()
        """
        target_chat = chat_id or settings.telegram_chat_id
        today = date.today()
        yesterday = today - timedelta(days=1)

        data = {
            "date": today.isoformat(),
            "top_movers": [],
            "watchlist_changes": [],
            "new_recommendations": [],
            "total_tickers": 0,
            "analyzed_count": 0,
        }

        # --- Top 5 movers ---
        # Find tickers with biggest absolute price change % (today vs yesterday)
        today_prices = await self.session.execute(
            select(
                DailyPrice.ticker_id,
                DailyPrice.close.label("today_close"),
                DailyPrice.date.label("price_date"),
            )
            .where(DailyPrice.date == today)
        )
        today_price_map = {row.ticker_id: row.today_close for row in today_prices.all()}

        yesterday_prices = await self.session.execute(
            select(DailyPrice.ticker_id, DailyPrice.close.label("yest_close"))
            .where(DailyPrice.date == yesterday)
        )
        yesterday_price_map = {row.ticker_id: row.yest_close for row in yesterday_prices.all()}

        # Calculate changes
        movers = []
        for ticker_id, today_close in today_price_map.items():
            yest_close = yesterday_price_map.get(ticker_id)
            if yest_close and yest_close > 0:
                change_pct = float((today_close - yest_close) / yest_close * 100)
                movers.append((ticker_id, float(today_close), change_pct))

        # Sort by absolute change descending, take top 5
        movers.sort(key=lambda x: abs(x[2]), reverse=True)
        top_movers = movers[:5]

        # Resolve symbols for top movers
        if top_movers:
            ticker_ids = [m[0] for m in top_movers]
            result = await self.session.execute(
                select(Ticker.id, Ticker.symbol)
                .where(Ticker.id.in_(ticker_ids))
            )
            id_to_symbol = {row.id: row.symbol for row in result.all()}
            data["top_movers"] = [
                {"symbol": id_to_symbol.get(tid, "?"), "close": close, "change_pct": change}
                for tid, close, change in top_movers
            ]

        data["total_tickers"] = len(today_price_map)

        # --- Watchlist signal changes ---
        if target_chat:
            watched_result = await self.session.execute(
                select(UserWatchlist.ticker_id, Ticker.symbol)
                .join(Ticker, Ticker.id == UserWatchlist.ticker_id)
                .where(UserWatchlist.chat_id == target_chat)
            )
            watched = watched_result.all()

            for ticker_id, symbol in watched:
                today_sig = await self.session.execute(
                    select(AIAnalysis.signal)
                    .where(
                        AIAnalysis.ticker_id == ticker_id,
                        AIAnalysis.analysis_type == AnalysisType.COMBINED,
                        AIAnalysis.analysis_date == today,
                    )
                )
                today_signal = today_sig.scalar_one_or_none()

                yest_sig = await self.session.execute(
                    select(AIAnalysis.signal)
                    .where(
                        AIAnalysis.ticker_id == ticker_id,
                        AIAnalysis.analysis_type == AnalysisType.COMBINED,
                        AIAnalysis.analysis_date == yesterday,
                    )
                )
                yest_signal = yest_sig.scalar_one_or_none()

                if today_signal and yest_signal and today_signal != yest_signal:
                    data["watchlist_changes"].append({
                        "symbol": symbol,
                        "old_signal": yest_signal,
                        "new_signal": today_signal,
                    })

        # --- New strong recommendations (mua with score >= 7) ---
        strong_result = await self.session.execute(
            select(AIAnalysis.signal, AIAnalysis.score, AIAnalysis.reasoning, Ticker.symbol)
            .join(Ticker, Ticker.id == AIAnalysis.ticker_id)
            .where(
                AIAnalysis.analysis_type == AnalysisType.COMBINED,
                AIAnalysis.analysis_date == today,
                AIAnalysis.signal == "mua",
                AIAnalysis.score >= 7,
            )
            .order_by(AIAnalysis.score.desc())
            .limit(5)
        )
        strong_recs = strong_result.all()
        data["new_recommendations"] = [
            {"symbol": r.symbol, "signal": r.signal, "score": r.score}
            for r in strong_recs
        ]
        data["analyzed_count"] = len(today_price_map)  # Approximate

        # --- Portfolio P&L (TBOT-04 + TBOT-06) ---
        try:
            from app.services.portfolio_service import PortfolioService
            portfolio_svc = PortfolioService(self.session)
            holdings = await portfolio_svc.get_holdings()
            if holdings:
                data["portfolio_holdings"] = holdings
                portfolio_summary = await portfolio_svc.get_summary()
                data["portfolio_summary"] = portfolio_summary
                data["owned_symbols"] = {h["symbol"] for h in holdings}
        except Exception as e:
            logger.warning(f"Failed to fetch portfolio data for daily summary: {e}")

        return data

    async def send_daily_summary(self) -> bool:
        """Build and send daily summary message.

        Called by the scheduled job. Returns True if sent successfully.
        """
        try:
            summary_data = await self.build_daily_summary()
            msg = MessageFormatter.daily_summary(summary_data)
            from app.telegram.bot import telegram_bot
            return await telegram_bot.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to build/send daily summary: {e}")
            return False
