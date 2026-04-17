"""Ex-date alert service for upcoming corporate events (CORP-07).

Scans corporate_events for upcoming ex-dates (within 3 business days)
for tickers the user holds or watches. Sends Telegram alerts, marks
alert_sent=True to prevent re-alerting.

Never raises — follows the same non-critical alert pattern as AlertService.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select, func as sa_func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.corporate_event import CorporateEvent
from app.models.lot import Lot
from app.models.ticker import Ticker
from app.models.user_watchlist import UserWatchlist
from app.telegram.formatter import MessageFormatter

# Lazy import — avoid circular dependency with bot module
telegram_bot = None


def _get_bot():
    """Lazy-load telegram_bot singleton."""
    global telegram_bot
    if telegram_bot is None:
        from app.telegram.bot import telegram_bot as _bot
        telegram_bot = _bot
    return telegram_bot


class ExDateAlertService:
    """Checks for upcoming ex-dates and sends Telegram alerts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_upcoming_exdates(self, chat_id: str | None = None) -> int:
        """Find events with ex_date in next 3 business days for held+watched tickers.

        Args:
            chat_id: Target Telegram chat ID. Falls back to settings.telegram_chat_id.

        Returns:
            Number of alerts successfully sent.
        """
        alerts_sent = 0
        try:
            target_chat = chat_id or settings.telegram_chat_id
            if not target_chat:
                logger.warning("No chat_id for ex-date alerts — skipping")
                return 0

            # Date range: today → today + 5 calendar days covers 3 business days
            # (worst case: Friday → covers Mon/Tue/Wed of next week)
            today = datetime.now(ZoneInfo(settings.timezone)).date()
            end_date = today + timedelta(days=5)

            # Query unsent events within date range
            events_result = await self.session.execute(
                select(
                    CorporateEvent.id,
                    CorporateEvent.ticker_id,
                    CorporateEvent.event_type,
                    CorporateEvent.ex_date,
                    CorporateEvent.dividend_amount,
                    CorporateEvent.ratio,
                )
                .where(
                    CorporateEvent.alert_sent == False,  # noqa: E712
                    CorporateEvent.ex_date >= today,
                    CorporateEvent.ex_date <= end_date,
                )
            )
            upcoming_events = events_result.all()

            if not upcoming_events:
                logger.info("No upcoming ex-date events to alert")
                return 0

            # Filter to Mon-Fri (weekday 0=Mon, 4=Fri) — skip weekend ex-dates
            upcoming_events = [
                e for e in upcoming_events
                if e.ex_date.weekday() <= 4
            ]

            if not upcoming_events:
                logger.info("No weekday ex-date events to alert")
                return 0

            # Get watchlisted ticker_ids
            wl_result = await self.session.execute(
                select(UserWatchlist.ticker_id)
                .where(UserWatchlist.chat_id == target_chat)
            )
            watchlisted_ids = {row.ticker_id for row in wl_result.all()}

            # Get held ticker_ids (lots with remaining_quantity > 0)
            held_result = await self.session.execute(
                select(Lot.ticker_id)
                .where(Lot.remaining_quantity > 0)
                .group_by(Lot.ticker_id)
            )
            held_ids = {row.ticker_id for row in held_result.all()}

            # Combine: must be in at least one set
            relevant_ids = watchlisted_ids | held_ids
            if not relevant_ids:
                logger.info("No watchlisted/held tickers — skipping ex-date alerts")
                return 0

            # Filter events to relevant tickers only
            relevant_events = [
                e for e in upcoming_events
                if e.ticker_id in relevant_ids
            ]

            if not relevant_events:
                logger.info("No ex-date events for watchlisted/held tickers")
                return 0

            # Resolve ticker symbols in bulk
            event_ticker_ids = {e.ticker_id for e in relevant_events}
            symbol_result = await self.session.execute(
                select(Ticker.id, Ticker.symbol)
                .where(Ticker.id.in_(event_ticker_ids))
            )
            id_to_symbol = {row.id: row.symbol for row in symbol_result.all()}

            # Send alerts
            bot = _get_bot()
            for event in relevant_events:
                try:
                    symbol = id_to_symbol.get(event.ticker_id, "???")
                    detail = self._build_detail(event)
                    msg = MessageFormatter.exdate_alert(
                        symbol=symbol,
                        event_type=event.event_type,
                        ex_date=event.ex_date.isoformat(),
                        detail=detail,
                    )
                    sent = await bot.send_message(msg, chat_id=target_chat)
                    if sent:
                        # Mark alert_sent=True (dedup — T-14-04 mitigation)
                        from sqlalchemy import update
                        await self.session.execute(
                            update(CorporateEvent)
                            .where(CorporateEvent.id == event.id)
                            .values(alert_sent=True)
                        )
                        await self.session.commit()
                        alerts_sent += 1
                except Exception as e:
                    logger.warning(f"Failed to send ex-date alert for event {event.id}: {e}")
                    continue

            logger.info(f"Ex-date alert check complete: {alerts_sent}/{len(relevant_events)} alerts sent")

        except Exception as e:
            logger.error(f"Ex-date alert check failed: {e}")

        return alerts_sent

    @staticmethod
    def _build_detail(event) -> str:
        """Build detail string for alert message."""
        if event.event_type == "CASH_DIVIDEND" and event.dividend_amount:
            return f"{event.dividend_amount:,.0f}đ/cp"
        if event.ratio and event.event_type in ("STOCK_DIVIDEND", "BONUS_SHARES", "RIGHTS_ISSUE"):
            return f"{event.ratio:g}:100"
        return ""
