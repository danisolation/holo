"""Daily pick generation service.

Scores existing trading signals, filters by capital and safety,
generates Vietnamese explanations via Gemini, persists to daily_picks table.

Pure computation functions are module-level for easy unit testing.
PickService class handles async DB operations and Gemini calls.
"""
from datetime import date
from decimal import Decimal

import google.genai as genai
from google.genai.errors import ClientError, ServerError
from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.daily_pick import DailyPick, PickStatus
from app.models.daily_price import DailyPrice
from app.models.technical_indicator import TechnicalIndicator
from app.models.ticker import Ticker
from app.models.user_risk_profile import UserRiskProfile
from app.schemas.picks import DailyPickResponse, DailyPicksResponse


# ── Pure computation functions ───────────────────────────────────────────────


def compute_composite_score(
    trading_signal_confidence: int,
    combined_score: int,
    safety_score: float,
) -> float:
    """Composite = confidence×0.4 + combined×0.3 + safety×0.3."""
    return (
        trading_signal_confidence * 0.4
        + combined_score * 0.3
        + safety_score * 0.3
    )


def is_affordable(capital: int, price: float) -> bool:
    """Check if user can afford at least 1 lot (100 shares) of this ticker."""
    return price * 100 <= capital


def compute_safety_score(
    atr_14: float,
    adx_14: float,
    avg_volume: int,
    current_price: float,
) -> float:
    """Safety score 0-10. High = safer pick.

    Components (each 0-10, then averaged):
    - ATR score: lower relative ATR = higher score (less volatile)
    - ADX score: higher ADX = higher score (stronger trend)
    - Volume score: higher volume = higher score (more liquid)
    """
    # ATR as % of price (relative volatility)
    atr_pct = (atr_14 / current_price * 100) if current_price > 0 else 10
    # Invert: low ATR% = high score. ATR% < 1% → 10, > 5% → 0
    atr_score = max(0, min(10, (5 - atr_pct) * 2.5))

    # ADX: > 25 = trending. Scale: 0 → 0, 25 → 5, 50+ → 10
    adx_score = max(0, min(10, adx_14 / 5))

    # Volume: > 500k = liquid. Scale: 0 → 0, 250k → 5, 500k+ → 10
    vol_score = max(0, min(10, avg_volume / 50000))

    return (atr_score + adx_score + vol_score) / 3


def extract_trading_plan(raw_response: dict) -> dict:
    """Extract entry/SL/TP from raw_response JSONB structure.

    Returns dict with: entry_price, stop_loss, take_profit_1, take_profit_2,
    risk_reward_ratio, position_size_pct, confidence.
    """
    long = raw_response.get("long_analysis", {})
    plan = long.get("trading_plan", {})
    return {
        "entry_price": plan.get("entry_price"),
        "stop_loss": plan.get("stop_loss"),
        "take_profit_1": plan.get("take_profit_1"),
        "take_profit_2": plan.get("take_profit_2"),
        "risk_reward_ratio": plan.get("risk_reward_ratio"),
        "position_size_pct": plan.get("position_size_pct", 10),
        "confidence": long.get("confidence", 5),
    }


def compute_position_sizing(
    capital: int,
    entry_price: float,
    position_pct: int,
) -> dict:
    """Compute VN lot-aligned position sizing.

    Caps position_pct at 30% max per RESEARCH.md.
    Returns: {shares, total_vnd, capital_pct}
    """
    position_pct = min(position_pct, 30)
    max_spend = capital * position_pct / 100
    lot_size = 100  # HOSE standard
    lots = int(max_spend / (entry_price * lot_size))
    if lots < 1:
        lots = 1  # Minimum 1 lot if affordable
    shares = lots * lot_size
    total_vnd = int(shares * entry_price)
    capital_pct = round(total_vnd / capital * 100, 1)
    return {
        "shares": shares,
        "total_vnd": total_vnd,
        "capital_pct": capital_pct,
    }


def generate_rejection_reason(
    rsi: float | None,
    atr_pct: float,
    adx: float | None,
    avg_volume: int,
    composite_score: float,
) -> str:
    """Generate a 1-line Vietnamese explanation for why ticker wasn't selected."""
    reasons: list[str] = []
    if rsi is not None and rsi > 70:
        reasons.append(f"RSI overbought ({rsi:.0f}), chờ pullback")
    if atr_pct > 4:
        reasons.append(f"Biến động cao (ATR {atr_pct:.1f}%)")
    if adx is not None and adx < 20:
        reasons.append(f"Xu hướng yếu (ADX {adx:.0f})")
    if avg_volume < 100_000:
        reasons.append(f"Volume quá thấp (avg {avg_volume:,.0f}/ngày)")
    if not reasons:
        reasons.append(f"Điểm tổng hợp thấp hơn ({composite_score:.1f})")
    return ", ".join(reasons[:2])  # Max 2 reasons per line


PICK_EXPLANATION_SYSTEM_INSTRUCTION = (
    "Bạn là huấn luyện viên đầu tư cá nhân cho nhà đầu tư mới tại Việt Nam. "
    "Viết giải thích 200-300 từ cho MỖI mã cổ phiếu được chọn. "
    "Phong cách: thân thiện, rõ ràng, như đang dạy bạn bè. "
    "Nội dung mỗi giải thích PHẢI bao gồm:\n"
    "1. Tại sao chọn mã này (kỹ thuật: RSI, MACD, support/resistance)\n"
    "2. Điểm mạnh cơ bản (P/E, ROE, tăng trưởng)\n"
    "3. Tâm lý thị trường hiện tại cho mã\n"
    "4. Rủi ro cần lưu ý và mức cắt lỗ\n"
    "KHÔNG dùng thuật ngữ tiếng Anh trừ tên chỉ báo (RSI, MACD, P/E). "
    "Dùng ví dụ số cụ thể từ dữ liệu.\n"
)


def build_explanation_prompt(picks_data: list[dict]) -> str:
    """Build Gemini prompt for Vietnamese pick explanations.

    Args:
        picks_data: list of dicts with symbol, entry_price, composite_score,
                    and optionally stop_loss, take_profit_1.
    """
    lines = ["Hãy viết giải thích cho các mã cổ phiếu sau:\n"]
    for i, p in enumerate(picks_data, 1):
        symbol = p.get("symbol", "???")
        entry = p.get("entry_price", 0)
        sl = p.get("stop_loss", 0)
        tp1 = p.get("take_profit_1", 0)
        score = p.get("composite_score", 0)
        lines.append(
            f"{i}. {symbol}: Giá vào {entry:,.0f}, SL {sl:,.0f}, "
            f"TP1 {tp1:,.0f}, Điểm tổng hợp {score:.1f}"
        )
    return "\n".join(lines)


# ── PickService class ────────────────────────────────────────────────────────


class PickService:
    """Daily pick generation and retrieval service."""

    def __init__(self, session: AsyncSession, api_key: str | None = None):
        self.session = session
        key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=key) if key else None
        self.model = settings.gemini_model

    async def get_or_create_profile(self) -> UserRiskProfile:
        """Get the single user risk profile, creating default if missing."""
        result = await self.session.execute(select(UserRiskProfile).limit(1))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = UserRiskProfile(
                capital=Decimal("50000000"),
                risk_level=3,
                broker_fee_pct=Decimal("0.150"),
            )
            self.session.add(profile)
            await self.session.flush()
            logger.info("Created default user risk profile: 50M VND, risk=3")
        return profile

    async def update_profile(self, capital: int, risk_level: int) -> UserRiskProfile:
        """Update the single user risk profile."""
        profile = await self.get_or_create_profile()
        profile.capital = Decimal(str(capital))
        profile.risk_level = risk_level
        await self.session.commit()
        logger.info(f"Updated profile: capital={capital:,}, risk_level={risk_level}")
        return profile

    async def generate_daily_picks(self) -> dict:
        """Generate daily stock picks from today's trading signals.

        Steps:
        1. Get user profile (capital, risk level)
        2. Query today's LONG trading signals
        3. Extract trading plan from raw_response
        4. Compute safety + composite scores
        5. Filter by affordability
        6. Select top 3-5 as picked, next 5-10 as almost
        7. Generate Gemini explanations for picked
        8. Compute position sizing for picked
        9. Persist to daily_picks table
        """
        today = date.today()
        profile = await self.get_or_create_profile()
        capital = int(profile.capital)

        # --- Step 1: Get today's LONG trading signals ---
        signal_query = (
            select(
                AIAnalysis.ticker_id,
                AIAnalysis.score,
                AIAnalysis.raw_response,
                Ticker.symbol,
                Ticker.name,
            )
            .join(Ticker, Ticker.id == AIAnalysis.ticker_id)
            .where(
                AIAnalysis.analysis_type == AnalysisType.TRADING_SIGNAL,
                AIAnalysis.signal == "long",
                AIAnalysis.analysis_date == today,
                AIAnalysis.score > 0,
            )
        )
        signal_rows = (await self.session.execute(signal_query)).all()
        logger.info(f"Found {len(signal_rows)} LONG trading signals for {today}")

        if not signal_rows:
            return {"picked": 0, "almost": 0, "date": str(today)}

        # --- Step 2: Get combined scores for today ---
        combined_query = (
            select(AIAnalysis.ticker_id, AIAnalysis.score)
            .where(
                AIAnalysis.analysis_type == AnalysisType.COMBINED,
                AIAnalysis.analysis_date == today,
            )
        )
        combined_rows = (await self.session.execute(combined_query)).all()
        combined_map = {row.ticker_id: row.score for row in combined_rows}

        # --- Step 3: Get technical indicators (latest) for safety scoring ---
        ticker_ids = [row.ticker_id for row in signal_rows]
        # Subquery: latest indicator date per ticker
        latest_date_sq = (
            select(
                TechnicalIndicator.ticker_id,
                func.max(TechnicalIndicator.date).label("max_date"),
            )
            .where(TechnicalIndicator.ticker_id.in_(ticker_ids))
            .group_by(TechnicalIndicator.ticker_id)
            .subquery()
        )
        indicator_query = (
            select(
                TechnicalIndicator.ticker_id,
                TechnicalIndicator.atr_14,
                TechnicalIndicator.adx_14,
                TechnicalIndicator.rsi_14,
            )
            .join(
                latest_date_sq,
                (TechnicalIndicator.ticker_id == latest_date_sq.c.ticker_id)
                & (TechnicalIndicator.date == latest_date_sq.c.max_date),
            )
        )
        indicator_rows = (await self.session.execute(indicator_query)).all()
        indicator_map = {
            row.ticker_id: {
                "atr_14": float(row.atr_14) if row.atr_14 is not None else None,
                "adx_14": float(row.adx_14) if row.adx_14 is not None else None,
                "rsi_14": float(row.rsi_14) if row.rsi_14 is not None else None,
            }
            for row in indicator_rows
        }

        # --- Step 4: Get recent avg volume + latest close price ---
        # Average volume over last 20 trading days
        vol_query = (
            select(
                DailyPrice.ticker_id,
                func.avg(DailyPrice.volume).label("avg_volume"),
            )
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= func.current_date() - 30,
            )
            .group_by(DailyPrice.ticker_id)
        )
        vol_rows = (await self.session.execute(vol_query)).all()
        volume_map = {row.ticker_id: int(row.avg_volume or 0) for row in vol_rows}

        # Latest close price per ticker
        latest_price_sq = (
            select(
                DailyPrice.ticker_id,
                func.max(DailyPrice.date).label("max_date"),
            )
            .where(DailyPrice.ticker_id.in_(ticker_ids))
            .group_by(DailyPrice.ticker_id)
            .subquery()
        )
        price_query = (
            select(DailyPrice.ticker_id, DailyPrice.close)
            .join(
                latest_price_sq,
                (DailyPrice.ticker_id == latest_price_sq.c.ticker_id)
                & (DailyPrice.date == latest_price_sq.c.max_date),
            )
        )
        price_rows = (await self.session.execute(price_query)).all()
        price_map = {row.ticker_id: float(row.close) for row in price_rows}

        # --- Step 5: Score each signal ---
        candidates = []
        for row in signal_rows:
            raw = row.raw_response or {}
            plan = extract_trading_plan(raw)
            entry_price = plan.get("entry_price")
            if not entry_price or entry_price <= 0:
                continue

            # Safety scoring
            indicators = indicator_map.get(row.ticker_id, {})
            atr = indicators.get("atr_14")
            adx = indicators.get("adx_14")
            rsi = indicators.get("rsi_14")
            avg_vol = volume_map.get(row.ticker_id, 0)
            current_price = price_map.get(row.ticker_id, float(entry_price))

            if atr is None or adx is None:
                # Skip tickers without ATR/ADX data
                continue

            safety = compute_safety_score(atr, adx, avg_vol, current_price)
            combined = combined_map.get(row.ticker_id, 5)  # Default 5 if missing
            composite = compute_composite_score(plan["confidence"], combined, safety)

            # ATR% for rejection reasons
            atr_pct = (atr / current_price * 100) if current_price > 0 else 10

            candidates.append({
                "ticker_id": row.ticker_id,
                "symbol": row.symbol,
                "name": row.name,
                "composite_score": composite,
                "entry_price": entry_price,
                "stop_loss": plan.get("stop_loss"),
                "take_profit_1": plan.get("take_profit_1"),
                "take_profit_2": plan.get("take_profit_2"),
                "risk_reward": plan.get("risk_reward_ratio"),
                "position_size_pct": plan.get("position_size_pct", 10),
                "confidence": plan["confidence"],
                "rsi": rsi,
                "atr_pct": atr_pct,
                "adx": adx,
                "avg_volume": avg_vol,
            })

        # --- Step 6: Filter by affordability ---
        candidates = [c for c in candidates if is_affordable(capital, c["entry_price"])]

        # --- Step 7: Sort and select ---
        candidates.sort(key=lambda c: c["composite_score"], reverse=True)
        candidates = candidates[:50]  # Top 50 maximum

        # Picked: top 3-5 with composite > 5.0 (min 3)
        picked = []
        for c in candidates:
            if len(picked) >= 5:
                break
            if c["composite_score"] > 5.0 or len(picked) < 3:
                picked.append(c)
            if len(picked) >= 3 and c["composite_score"] <= 5.0:
                break

        # Almost: next 5-10 after picked
        picked_ids = {c["ticker_id"] for c in picked}
        almost = [c for c in candidates if c["ticker_id"] not in picked_ids][:10]

        # --- Step 8: Generate Gemini explanations for picked ---
        explanations = {}
        if picked and self.client:
            try:
                prompt = build_explanation_prompt(picked)
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=PICK_EXPLANATION_SYSTEM_INSTRUCTION,
                        temperature=0.7,
                        max_output_tokens=8192,
                    ),
                )
                if response and response.text:
                    # Split explanation by numbered picks
                    text = response.text
                    # Store full text - split per symbol later
                    for p in picked:
                        sym = p["symbol"]
                        # Find section for this symbol
                        idx = text.find(sym)
                        if idx >= 0:
                            # Find next symbol or end
                            next_idx = len(text)
                            for other in picked:
                                if other["symbol"] != sym:
                                    oi = text.find(other["symbol"], idx + len(sym))
                                    if oi > idx and oi < next_idx:
                                        next_idx = oi
                            explanations[sym] = text[idx:next_idx].strip()
                    logger.info(f"Gemini explanations generated for {len(explanations)} picks")
            except (ClientError, ServerError, Exception) as e:
                logger.warning(f"Gemini explanation failed (picks still valid): {e}")

        # --- Step 9: Position sizing for picked ---
        for p in picked:
            sizing = compute_position_sizing(capital, p["entry_price"], p["position_size_pct"])
            p["position_size_shares"] = sizing["shares"]
            p["position_size_vnd"] = sizing["total_vnd"]
            p["position_size_pct_computed"] = sizing["capital_pct"]

        # --- Step 10: Delete existing picks for today (idempotent re-run) ---
        await self.session.execute(
            delete(DailyPick).where(DailyPick.pick_date == today)
        )

        # --- Step 11: Insert picked rows ---
        for rank, p in enumerate(picked, 1):
            pick = DailyPick(
                pick_date=today,
                ticker_id=p["ticker_id"],
                rank=rank,
                composite_score=Decimal(str(round(p["composite_score"], 2))),
                entry_price=Decimal(str(p["entry_price"])) if p["entry_price"] else None,
                stop_loss=Decimal(str(p["stop_loss"])) if p.get("stop_loss") else None,
                take_profit_1=Decimal(str(p["take_profit_1"])) if p.get("take_profit_1") else None,
                take_profit_2=Decimal(str(p["take_profit_2"])) if p.get("take_profit_2") else None,
                risk_reward=Decimal(str(p["risk_reward"])) if p.get("risk_reward") else None,
                position_size_shares=p.get("position_size_shares"),
                position_size_vnd=p.get("position_size_vnd"),
                position_size_pct=Decimal(str(p.get("position_size_pct_computed", 0))),
                explanation=explanations.get(p["symbol"]),
                status=PickStatus.PICKED.value,
            )
            self.session.add(pick)

        # --- Step 12: Insert almost rows ---
        for p in almost:
            reason = generate_rejection_reason(
                rsi=p.get("rsi"),
                atr_pct=p.get("atr_pct", 0),
                adx=p.get("adx"),
                avg_volume=p.get("avg_volume", 0),
                composite_score=p["composite_score"],
            )
            pick = DailyPick(
                pick_date=today,
                ticker_id=p["ticker_id"],
                rank=None,
                composite_score=Decimal(str(round(p["composite_score"], 2))),
                entry_price=Decimal(str(p["entry_price"])) if p["entry_price"] else None,
                stop_loss=Decimal(str(p["stop_loss"])) if p.get("stop_loss") else None,
                take_profit_1=Decimal(str(p["take_profit_1"])) if p.get("take_profit_1") else None,
                take_profit_2=Decimal(str(p["take_profit_2"])) if p.get("take_profit_2") else None,
                risk_reward=Decimal(str(p["risk_reward"])) if p.get("risk_reward") else None,
                status=PickStatus.ALMOST.value,
                rejection_reason=reason,
            )
            self.session.add(pick)

        await self.session.commit()

        result = {
            "picked": len(picked),
            "almost": len(almost),
            "date": str(today),
            "symbols": [p["symbol"] for p in picked],
        }
        logger.info(f"Daily picks generated: {result}")
        return result

    async def get_today_picks(self, capital: int) -> dict:
        """Get today's picks with position sizing recomputed for given capital.

        Returns dict ready for DailyPicksResponse serialization.
        """
        today = date.today()

        query = (
            select(DailyPick, Ticker.symbol, Ticker.name)
            .join(Ticker, Ticker.id == DailyPick.ticker_id)
            .where(DailyPick.pick_date == today)
            .order_by(DailyPick.rank.nulls_last(), DailyPick.composite_score.desc())
        )
        rows = (await self.session.execute(query)).all()

        picks_list = []
        almost_list = []

        for pick, symbol, name in rows:
            entry = float(pick.entry_price) if pick.entry_price else None

            # Recompute position sizing with current capital for picked
            if pick.status == PickStatus.PICKED.value and entry and entry > 0:
                pct = float(pick.position_size_pct) if pick.position_size_pct else 10
                sizing = compute_position_sizing(capital, entry, int(pct))
            else:
                sizing = {"shares": None, "total_vnd": None, "capital_pct": None}

            item = DailyPickResponse(
                pick_date=str(pick.pick_date),
                ticker_symbol=symbol,
                ticker_name=name,
                rank=pick.rank,
                composite_score=float(pick.composite_score),
                entry_price=entry,
                stop_loss=float(pick.stop_loss) if pick.stop_loss else None,
                take_profit_1=float(pick.take_profit_1) if pick.take_profit_1 else None,
                take_profit_2=float(pick.take_profit_2) if pick.take_profit_2 else None,
                risk_reward=float(pick.risk_reward) if pick.risk_reward else None,
                position_size_shares=sizing.get("shares"),
                position_size_vnd=sizing.get("total_vnd"),
                position_size_pct=sizing.get("capital_pct"),
                explanation=pick.explanation,
                status=pick.status,
                rejection_reason=pick.rejection_reason,
            )

            if pick.status == PickStatus.PICKED.value:
                picks_list.append(item)
            else:
                almost_list.append(item)

        return DailyPicksResponse(
            date=str(today),
            capital=capital,
            picks=picks_list,
            almost_selected=almost_list,
        )

    async def get_pick_history(self, days: int = 30) -> list[dict]:
        """Get pick history for the last N days. Cap at 365 per T-43-06."""
        days = min(days, 365)
        today = date.today()

        query = (
            select(DailyPick, Ticker.symbol, Ticker.name)
            .join(Ticker, Ticker.id == DailyPick.ticker_id)
            .where(
                DailyPick.pick_date >= func.current_date() - days,
                DailyPick.status == PickStatus.PICKED.value,
            )
            .order_by(DailyPick.pick_date.desc(), DailyPick.rank)
        )
        rows = (await self.session.execute(query)).all()

        history = []
        for pick, symbol, name in rows:
            history.append({
                "pick_date": str(pick.pick_date),
                "ticker_symbol": symbol,
                "ticker_name": name,
                "rank": pick.rank,
                "composite_score": float(pick.composite_score),
                "entry_price": float(pick.entry_price) if pick.entry_price else None,
                "status": pick.status,
            })
        return history
