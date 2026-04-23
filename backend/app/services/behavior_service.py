"""Behavior tracking service.

Pure computation functions for habit detection, sector scoring, and risk checks.
BehaviorService class handles async DB operations for behavior CRUD.

Pure functions are module-level for easy unit testing without DB.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior_event import BehaviorEvent
from app.models.daily_price import DailyPrice
from app.models.habit_detection import HabitDetection
from app.models.news_article import NewsArticle
from app.models.risk_suggestion import RiskSuggestion
from app.models.sector_preference import SectorPreference
from app.models.ticker import Ticker
from app.models.trade import Trade
from app.models.user_risk_profile import UserRiskProfile


# ── Pure computation functions ───────────────────────────────────────────────


def detect_premature_profit_taking(
    sell_price: float,
    prices_after_sell: list[float],
    threshold_pct: float = 5.0,
) -> bool:
    """Check if price rose >threshold% after selling.

    Args:
        sell_price: The price at which the trade was sold.
        prices_after_sell: Close prices after the sell date.
        threshold_pct: Percentage rise threshold (exclusive).

    Returns:
        True if max post-sell price exceeds sell_price by >threshold_pct.
    """
    if not prices_after_sell or sell_price <= 0:
        return False
    max_after = max(prices_after_sell)
    rise_pct = ((max_after - sell_price) / sell_price) * 100
    return rise_pct > threshold_pct


def detect_holding_losers(
    buy_price: float,
    current_price: float,
    days_held: int,
    loss_threshold_pct: float = 10.0,
    min_days: int = 5,
) -> bool:
    """Check if open position has unrealized loss >threshold% held >min_days.

    Args:
        buy_price: Original buy price.
        current_price: Current market price.
        days_held: Number of trading days held.
        loss_threshold_pct: Unrealized loss percentage threshold (exclusive).
        min_days: Minimum days held threshold (exclusive).

    Returns:
        True if loss exceeds threshold AND held longer than min_days.
    """
    if buy_price <= 0:
        return False
    loss_pct = ((buy_price - current_price) / buy_price) * 100
    return loss_pct > loss_threshold_pct and days_held > min_days


def detect_impulsive_trade(
    trade_created_at: datetime,
    news_timestamps: list[datetime],
    window_hours: float = 2.0,
) -> bool:
    """Check if trade was created within window_hours after a news article.

    Args:
        trade_created_at: When the trade was created (TIMESTAMP).
        news_timestamps: Published timestamps of news about the same ticker.
        window_hours: Hours window (exclusive) — news must be BEFORE trade.

    Returns:
        True if any news was published within window_hours before the trade.
    """
    window = timedelta(hours=window_hours)
    for news_ts in news_timestamps:
        # News must be BEFORE trade, and gap must be less than window
        gap = trade_created_at - news_ts
        if timedelta(0) < gap < window:
            return True
    return False


def compute_preference_score(win_rate: float, normalized_pnl: float) -> float:
    """Compute sector preference score.

    Formula: (win_rate × 0.6) + (normalized_pnl × 0.4)
    Uses centered normalization so poor sectors get negative scores.

    Args:
        win_rate: Win rate as fraction (0.0 to 1.0).
        normalized_pnl: Centered-normalized P&L (-1.0 to 1.0 range).

    Returns:
        Preference score (can be negative for poor-performing sectors).
    """
    return (win_rate * 0.6) + (normalized_pnl * 0.4)


def check_consecutive_losses_pure(
    recent_sell_pnls: list[float],
    current_risk_level: int,
    has_pending_suggestion: bool,
) -> dict | None:
    """Check if last 3 SELL P&Ls are all negative → suggest risk reduction.

    Args:
        recent_sell_pnls: Last N SELL trade net_pnl values (most recent first).
        current_risk_level: Current user risk level (1-5).
        has_pending_suggestion: Whether a pending risk suggestion already exists.

    Returns:
        Dict with current_level, suggested_level, reason — or None.
    """
    if len(recent_sell_pnls) < 3:
        return None
    if has_pending_suggestion:
        return None
    if current_risk_level <= 1:
        return None

    last_three = recent_sell_pnls[:3]
    if all(pnl < 0 for pnl in last_three):
        formatted = ", ".join(f"{pnl:,.0f}" for pnl in last_three)
        return {
            "current_level": current_risk_level,
            "suggested_level": current_risk_level - 1,
            "reason": f"3 lần lỗ liên tiếp ({formatted} VND)",
        }
    return None


# ── BehaviorService (async DB operations) ────────────────────────────────────


class BehaviorService:
    """Async service for behavior tracking operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(self, event_type: str, ticker_id: int | None, event_metadata: dict | None = None) -> int:
        """Insert behavior_event row, return ID."""
        event = BehaviorEvent(
            event_type=event_type,
            ticker_id=ticker_id,
            event_metadata=event_metadata,
        )
        self.session.add(event)
        await self.session.flush()
        logger.debug(f"Logged behavior event: {event_type} ticker_id={ticker_id}")
        return event.id

    async def get_viewing_stats(self, limit: int = 10) -> dict:
        """Aggregate behavior_events by ticker_id, return top N with view_count, last_viewed, sector.

        Returns dict matching ViewingStatsResponse schema.
        """
        result = await self.session.execute(
            select(
                BehaviorEvent.ticker_id,
                Ticker.symbol.label("ticker_symbol"),
                Ticker.sector,
                func.count().label("view_count"),
                func.max(BehaviorEvent.created_at).label("last_viewed"),
            )
            .join(Ticker, BehaviorEvent.ticker_id == Ticker.id)
            .where(BehaviorEvent.event_type == "ticker_view")
            .where(BehaviorEvent.ticker_id.isnot(None))
            .group_by(BehaviorEvent.ticker_id, Ticker.symbol, Ticker.sector)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rows = result.all()

        total_result = await self.session.execute(
            select(func.count())
            .select_from(BehaviorEvent)
            .where(BehaviorEvent.event_type == "ticker_view")
        )
        total_views = total_result.scalar() or 0

        return {
            "items": [
                {
                    "ticker_symbol": row.ticker_symbol,
                    "sector": row.sector,
                    "view_count": row.view_count,
                    "last_viewed": row.last_viewed.isoformat() if row.last_viewed else "",
                }
                for row in rows
            ],
            "total_views": total_views,
        }

    async def detect_all_habits(self) -> dict:
        """Run all 3 habit detections on trades. Returns habit counts + details.

        Per CONTEXT.md: weekly batch, not real-time.
        """
        habits_found: dict[str, list] = {
            "premature_sell": [],
            "holding_losers": [],
            "impulsive_trade": [],
        }

        # ── 1. Premature profit-taking ───────────────────────────────────
        # SELL trades with positive net_pnl, at least 5 trading days ago (Pitfall 1)
        from datetime import date as date_type, timedelta as td
        cutoff_date = date_type.today() - td(days=7)  # ~5 trading days

        sell_trades_result = await self.session.execute(
            select(Trade, Ticker.symbol)
            .join(Ticker, Trade.ticker_id == Ticker.id)
            .where(Trade.side == "SELL")
            .where(Trade.net_pnl > 0)
            .where(Trade.trade_date <= cutoff_date)
        )
        sell_trades = sell_trades_result.all()

        if sell_trades:
            # Batch query for post-sell prices (Pitfall 6: avoid N+1)
            ticker_date_pairs = [(t.Trade.ticker_id, t.Trade.trade_date) for t in sell_trades]
            all_ticker_ids = list({tid for tid, _ in ticker_date_pairs})
            min_date = min(d for _, d in ticker_date_pairs)

            prices_result = await self.session.execute(
                select(DailyPrice.ticker_id, DailyPrice.date, DailyPrice.close)
                .where(DailyPrice.ticker_id.in_(all_ticker_ids))
                .where(DailyPrice.date > min_date)
            )
            prices_by_ticker: dict[int, list[tuple]] = {}
            for row in prices_result.all():
                prices_by_ticker.setdefault(row.ticker_id, []).append(
                    (row.date, float(row.close))
                )

            for row in sell_trades:
                trade = row.Trade
                ticker_prices = prices_by_ticker.get(trade.ticker_id, [])
                post_sell_prices = [p for d, p in ticker_prices if d > trade.trade_date]

                if detect_premature_profit_taking(float(trade.price), post_sell_prices):
                    habits_found["premature_sell"].append({
                        "trade_id": trade.id,
                        "ticker_id": trade.ticker_id,
                        "ticker_symbol": row.symbol,
                        "sell_price": float(trade.price),
                        "max_after": max(post_sell_prices) if post_sell_prices else None,
                    })

        # ── 2. Holding losers ────────────────────────────────────────────
        # Open BUY trades with unrealized loss >10% held >5 days
        from app.models.lot import Lot

        open_lots_result = await self.session.execute(
            select(Lot, Trade.price.label("buy_price"), Trade.trade_date, Ticker.symbol, Trade.ticker_id)
            .join(Trade, Lot.trade_id == Trade.id)
            .join(Ticker, Trade.ticker_id == Ticker.id)
            .where(Lot.remaining_quantity > 0)
        )
        open_lots = open_lots_result.all()

        if open_lots:
            open_ticker_ids = list({r.ticker_id for r in open_lots})
            # Get latest close price for each ticker
            from sqlalchemy import literal_column
            latest_prices_result = await self.session.execute(
                select(
                    DailyPrice.ticker_id,
                    DailyPrice.close,
                )
                .distinct(DailyPrice.ticker_id)
                .where(DailyPrice.ticker_id.in_(open_ticker_ids))
                .order_by(DailyPrice.ticker_id, DailyPrice.date.desc())
            )
            latest_prices = {row.ticker_id: float(row.close) for row in latest_prices_result.all()}

            for row in open_lots:
                current_price = latest_prices.get(row.ticker_id)
                if current_price is None:
                    continue
                days_held = (date_type.today() - row.trade_date).days
                buy_price = float(row.buy_price)

                if detect_holding_losers(buy_price, current_price, days_held):
                    habits_found["holding_losers"].append({
                        "trade_id": row.Lot.trade_id,
                        "ticker_id": row.ticker_id,
                        "ticker_symbol": row.symbol,
                        "buy_price": buy_price,
                        "current_price": current_price,
                        "days_held": days_held,
                    })

        # ── 3. Impulsive trading ─────────────────────────────────────────
        # BUY trades where created_at is within 2 hours of NewsArticle.published_at (Pitfall 2)
        buy_trades_result = await self.session.execute(
            select(Trade, Ticker.symbol)
            .join(Ticker, Trade.ticker_id == Ticker.id)
            .where(Trade.side == "BUY")
            .where(Trade.created_at >= datetime.now() - timedelta(days=30))
        )
        buy_trades = buy_trades_result.all()

        if buy_trades:
            buy_ticker_ids = list({t.Trade.ticker_id for t in buy_trades})
            news_result = await self.session.execute(
                select(NewsArticle.ticker_id, NewsArticle.published_at)
                .where(NewsArticle.ticker_id.in_(buy_ticker_ids))
            )
            news_by_ticker: dict[int, list[datetime]] = {}
            for row in news_result.all():
                news_by_ticker.setdefault(row.ticker_id, []).append(row.published_at)

            for row in buy_trades:
                trade = row.Trade
                news_times = news_by_ticker.get(trade.ticker_id, [])
                if trade.created_at and detect_impulsive_trade(trade.created_at, news_times):
                    habits_found["impulsive_trade"].append({
                        "trade_id": trade.id,
                        "ticker_id": trade.ticker_id,
                        "ticker_symbol": row.symbol,
                    })

        # ── Store results in habit_detections table ──────────────────────
        new_detections = 0
        for habit_type, detections in habits_found.items():
            for det in detections:
                # Dedup: skip if same habit+trade already detected
                existing = await self.session.execute(
                    select(HabitDetection.id).where(
                        HabitDetection.habit_type == habit_type,
                        HabitDetection.trade_id == det["trade_id"],
                    ).limit(1)
                )
                if existing.scalar_one_or_none() is not None:
                    continue
                detection = HabitDetection(
                    habit_type=habit_type,
                    ticker_id=det["ticker_id"],
                    trade_id=det["trade_id"],
                    evidence=det,
                )
                self.session.add(detection)
                new_detections += 1

        if new_detections > 0:
            await self.session.flush()

        logger.info(
            f"Habit detection complete: {sum(len(v) for v in habits_found.values())} patterns found "
            f"(premature_sell={len(habits_found['premature_sell'])}, "
            f"holding_losers={len(habits_found['holding_losers'])}, "
            f"impulsive_trade={len(habits_found['impulsive_trade'])})"
        )

        return {
            "premature_sell": len(habits_found["premature_sell"]),
            "holding_losers": len(habits_found["holding_losers"]),
            "impulsive_trade": len(habits_found["impulsive_trade"]),
            "total": new_detections,
        }

    async def get_habit_detections(self) -> dict:
        """Read stored habit detections from DB (not re-detect).

        Returns dict matching HabitDetectionsResponse schema.
        Used by GET /api/behavior/habits — weekly batch job writes, this reads.
        """
        result = await self.session.execute(
            select(
                HabitDetection.habit_type,
                func.count().label("count"),
                func.max(HabitDetection.detected_at).label("latest_date"),
            )
            .group_by(HabitDetection.habit_type)
        )
        rows = result.all()

        # Get latest ticker for each habit type
        habits = []
        for row in rows:
            # Get the latest detection's ticker symbol
            latest_result = await self.session.execute(
                select(Ticker.symbol)
                .join(HabitDetection, HabitDetection.ticker_id == Ticker.id)
                .where(HabitDetection.habit_type == row.habit_type)
                .order_by(HabitDetection.detected_at.desc())
                .limit(1)
            )
            latest_ticker = latest_result.scalar_one_or_none()

            habits.append({
                "habit_type": row.habit_type,
                "count": row.count,
                "latest_ticker": latest_ticker,
                "latest_date": row.latest_date.isoformat() if row.latest_date else None,
            })

        # Get the most recent analysis date
        analysis_date_result = await self.session.execute(
            select(func.max(HabitDetection.detected_at))
        )
        analysis_date_raw = analysis_date_result.scalar_one_or_none()

        return {
            "habits": habits,
            "analysis_date": analysis_date_raw.isoformat() if analysis_date_raw else None,
        }

    async def check_consecutive_losses(self) -> dict | None:
        """Check if last 3 SELL trades are all losses. Create risk_suggestion if so.

        Per ADPT-01: only 1 pending suggestion at a time.
        Order by trade_date DESC, id DESC (Pitfall 3).
        """
        # Get last 3 SELL trade P&Ls
        result = await self.session.execute(
            select(Trade.net_pnl)
            .where(Trade.side == "SELL")
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .limit(3)
        )
        recent_pnls = [float(row.net_pnl) for row in result.all() if row.net_pnl is not None]

        # Check for pending suggestion
        pending_result = await self.session.execute(
            select(RiskSuggestion).where(RiskSuggestion.status == "pending")
        )
        has_pending = pending_result.scalar_one_or_none() is not None

        # Get current risk level
        profile = await self._get_risk_profile()
        current_risk = profile.risk_level if profile else 3

        suggestion_data = check_consecutive_losses_pure(recent_pnls, current_risk, has_pending)
        if suggestion_data is None:
            return None

        # Create risk suggestion
        suggestion = RiskSuggestion(
            current_level=suggestion_data["current_level"],
            suggested_level=suggestion_data["suggested_level"],
            reason=suggestion_data["reason"],
        )
        self.session.add(suggestion)
        await self.session.flush()
        logger.info(f"Created risk suggestion: {suggestion_data['current_level']} → {suggestion_data['suggested_level']}")

        return suggestion_data

    async def get_pending_risk_suggestion(self) -> RiskSuggestion | None:
        """Return pending risk suggestion or None."""
        result = await self.session.execute(
            select(RiskSuggestion)
            .where(RiskSuggestion.status == "pending")
            .order_by(RiskSuggestion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def respond_to_risk_suggestion(self, suggestion_id: int, action: str) -> RiskSuggestion:
        """Accept or reject risk suggestion.

        T-46-04 mitigation: validates suggestion exists AND status="pending" before allowing response.
        If accept: update UserRiskProfile.risk_level.
        """
        result = await self.session.execute(
            select(RiskSuggestion).where(
                RiskSuggestion.id == suggestion_id,
                RiskSuggestion.status == "pending",
            )
        )
        suggestion = result.scalar_one_or_none()
        if suggestion is None:
            raise ValueError(f"No pending risk suggestion found with id={suggestion_id}")

        suggestion.status = "accepted" if action == "accept" else "rejected"
        suggestion.responded_at = func.now()

        if action == "accept":
            profile = await self._get_risk_profile()
            if profile:
                profile.risk_level = suggestion.suggested_level
                logger.info(f"Risk level updated: {suggestion.current_level} → {suggestion.suggested_level}")

        await self.session.flush()
        return suggestion

    async def compute_sector_preferences(self) -> list[dict]:
        """Compute sector preferences from trades grouped by ticker.sector.

        Per ADPT-02: preference_score = (win_rate × 0.6) + (normalized_pnl × 0.4).
        Uses centered normalization (subtract mean) so poor sectors get multiplier < 1.0.
        Upsert into sector_preferences table. Only sectors with >=1 trade included.
        """
        # Aggregate trades by sector
        result = await self.session.execute(
            select(
                Ticker.sector,
                func.count().label("total_trades"),
                func.sum(case((Trade.net_pnl > 0, 1), else_=0)).label("win_count"),
                func.sum(case((Trade.net_pnl < 0, 1), else_=0)).label("loss_count"),
                func.coalesce(func.sum(Trade.net_pnl), 0).label("net_pnl"),
            )
            .join(Ticker, Trade.ticker_id == Ticker.id)
            .where(Trade.side == "SELL")
            .where(Ticker.sector.isnot(None))
            .group_by(Ticker.sector)
        )
        rows = result.all()

        if not rows:
            return []

        # Compute per-sector stats
        sector_data = []
        all_pnls = []
        for row in rows:
            total = row.total_trades
            wins = row.win_count or 0
            pnl = float(row.net_pnl)
            all_pnls.append(pnl)
            sector_data.append({
                "sector": row.sector,
                "total_trades": total,
                "win_count": wins,
                "loss_count": row.loss_count or 0,
                "net_pnl": pnl,
                "win_rate": wins / total if total > 0 else 0.0,
            })

        # Centered normalization for P&L (subtract mean so poor sectors get < 0)
        mean_pnl = sum(all_pnls) / len(all_pnls) if all_pnls else 0.0
        max_abs = max(abs(p - mean_pnl) for p in all_pnls) if all_pnls else 1.0
        if max_abs == 0:
            max_abs = 1.0  # Avoid division by zero

        for sd in sector_data:
            normalized_pnl = (sd["net_pnl"] - mean_pnl) / max_abs
            sd["preference_score"] = compute_preference_score(sd["win_rate"], normalized_pnl)

        # Upsert into sector_preferences table
        for sd in sector_data:
            existing_result = await self.session.execute(
                select(SectorPreference).where(SectorPreference.sector == sd["sector"])
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                existing.total_trades = sd["total_trades"]
                existing.win_count = sd["win_count"]
                existing.loss_count = sd["loss_count"]
                existing.net_pnl = Decimal(str(sd["net_pnl"]))
                existing.preference_score = Decimal(str(round(sd["preference_score"], 3)))
                existing.updated_at = func.now()
            else:
                pref = SectorPreference(
                    sector=sd["sector"],
                    total_trades=sd["total_trades"],
                    win_count=sd["win_count"],
                    loss_count=sd["loss_count"],
                    net_pnl=Decimal(str(sd["net_pnl"])),
                    preference_score=Decimal(str(round(sd["preference_score"], 3))),
                )
                self.session.add(pref)

        await self.session.flush()
        logger.info(f"Computed sector preferences for {len(sector_data)} sectors")
        return sector_data

    async def get_sector_preferences(self) -> dict:
        """Return sector preferences ordered by preference_score DESC.

        Include insufficient_count (sectors with < 3 trades per ADPT-02).
        """
        result = await self.session.execute(
            select(SectorPreference).order_by(SectorPreference.preference_score.desc())
        )
        prefs = result.scalars().all()

        insufficient_count = sum(1 for p in prefs if p.total_trades < 3)

        return {
            "sectors": [
                {
                    "sector": p.sector,
                    "total_trades": p.total_trades,
                    "win_count": p.win_count,
                    "loss_count": p.loss_count,
                    "net_pnl": float(p.net_pnl),
                    "win_rate": round(p.win_count / p.total_trades * 100, 1) if p.total_trades > 0 else 0.0,
                    "preference_score": float(p.preference_score),
                }
                for p in prefs
            ],
            "insufficient_count": insufficient_count,
        }

    async def _get_risk_profile(self) -> UserRiskProfile | None:
        """Get or create user risk profile."""
        result = await self.session.execute(select(UserRiskProfile).limit(1))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = UserRiskProfile()
            self.session.add(profile)
            await self.session.flush()
        return profile
