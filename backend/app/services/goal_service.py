"""Goal service — monthly targets, weekly prompts, and AI weekly reviews.

Pure computation functions for progress calculation and risk clamping.
GoalService class handles async DB operations and Gemini review generation.

Pure functions are module-level for easy unit testing without DB.
"""
import json
from datetime import date, timedelta
from decimal import Decimal

import google.genai as genai
from google.genai.errors import ClientError, ServerError
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import func as sa_func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models.daily_pick import DailyPick
from app.models.habit_detection import HabitDetection
from app.models.trade import Trade
from app.models.trading_goal import TradingGoal
from app.models.user_risk_profile import UserRiskProfile
from app.models.weekly_prompt import WeeklyPrompt
from app.models.weekly_review import WeeklyReview


# ── Gemini structured output schema ─────────────────────────────────────────


class WeeklyReviewOutput(BaseModel):
    """Structured output schema for Gemini weekly review generation."""
    summary_text: str
    highlights: dict  # {"good": [...], "bad": [...]}
    suggestions: list[str]


WEEKLY_REVIEW_SYSTEM_INSTRUCTION = (
    "Bạn là huấn luyện viên giao dịch chứng khoán cá nhân. "
    "Viết bản đánh giá tuần bằng tiếng Việt (300-500 từ). "
    "Phân tích khách quan: điểm tốt, điểm cần cải thiện, và đề xuất hành động cụ thể cho tuần tới. "
    "Giọng văn chuyên nghiệp nhưng thân thiện, dùng thuật ngữ chứng khoán Việt Nam."
)


# ── Pure computation functions ───────────────────────────────────────────────


def compute_goal_progress(actual_pnl: float, target_pnl: float) -> dict:
    """Compute goal progress percentage and color indicator.

    Args:
        actual_pnl: Realized P&L from SELL trades this month.
        target_pnl: Monthly profit target.

    Returns:
        {"percentage": float (0-200), "color": "green"|"amber"|"red"}
    """
    if target_pnl <= 0:
        return {"percentage": 0.0, "color": "red"}

    pct = (actual_pnl / target_pnl) * 100
    pct = max(0.0, pct)       # Negative actual → 0%
    pct = min(200.0, pct)     # Cap at 200%
    pct = round(pct, 1)

    if pct >= 100:
        color = "green"
    elif pct >= 50:
        color = "amber"
    else:
        color = "red"

    return {"percentage": pct, "color": color}


def clamp_risk_level(current: int, delta: int) -> int:
    """Clamp risk level to 1-5 range after applying delta.

    Args:
        current: Current risk level (1-5).
        delta: Change to apply (-1 for cautious, 0 for unchanged, +1 for aggressive).

    Returns:
        New risk level clamped to [1, 5].
    """
    return max(1, min(5, current + delta))


def build_review_prompt(
    trades_data: list[dict],
    habit_data: list[dict],
    pick_outcomes: list[dict],
    risk_level: int,
    goal_progress: dict | None,
) -> str:
    """Build Vietnamese weekly review prompt for Gemini.

    Args:
        trades_data: List of trade dicts with ticker, side, pnl keys.
        habit_data: List of detected habit dicts with habit_type, ticker keys.
        pick_outcomes: List of daily pick outcome dicts.
        risk_level: Current user risk level (1-5).
        goal_progress: Goal progress dict or None if no active goal.

    Returns:
        Complete prompt string for Gemini review generation.
    """
    sections = []

    # Trade summary
    if trades_data:
        trade_lines = []
        for t in trades_data:
            pnl_str = f", PnL: {t.get('pnl', 0):,.0f} VND" if t.get("pnl") else ""
            trade_lines.append(f"  - {t.get('ticker', '?')} ({t.get('side', '?')}{pnl_str})")
        sections.append(f"Giao dịch trong tuần ({len(trades_data)} lệnh):\n" + "\n".join(trade_lines))
    else:
        sections.append("Tuần này không có giao dịch nào.")

    # Habit detections
    if habit_data:
        habit_lines = [f"  - {h.get('habit_type', '?')}: {h.get('ticker', '?')}" for h in habit_data]
        sections.append("Thói quen phát hiện:\n" + "\n".join(habit_lines))

    # Pick outcomes
    if pick_outcomes:
        pick_lines = [f"  - {p.get('ticker', '?')}: {p.get('outcome', '?')}" for p in pick_outcomes]
        sections.append("Kết quả gợi ý hàng ngày:\n" + "\n".join(pick_lines))

    # Risk level
    sections.append(f"Mức độ rủi ro hiện tại: {risk_level}/5")

    # Goal progress
    if goal_progress:
        sections.append(
            f"Tiến độ mục tiêu tháng: {goal_progress.get('percentage', 0)}% "
            f"({goal_progress.get('color', 'N/A')})"
        )

    prompt = (
        "Dữ liệu giao dịch tuần qua:\n\n"
        + "\n\n".join(sections)
        + "\n\nHãy viết bản đánh giá tuần bằng tiếng Việt theo format JSON với các trường: "
        "summary_text (300-500 từ), highlights (object với good và bad là arrays), "
        "suggestions (array các đề xuất cụ thể)."
    )
    return prompt


def parse_review_response(response_data: dict | None) -> dict:
    """Parse and validate Gemini review response with fallback.

    Args:
        response_data: Parsed response dict from Gemini, or None if failed.

    Returns:
        Cleaned dict with summary_text, highlights, suggestions.
    """
    fallback = {
        "summary_text": "Không thể tạo nhận xét tuần. Vui lòng thử lại.",
        "highlights": {"good": [], "bad": []},
        "suggestions": [],
    }

    if response_data is None or not isinstance(response_data, dict):
        return fallback

    summary_text = response_data.get("summary_text")
    if not summary_text or not isinstance(summary_text, str):
        return fallback

    # Validate/fill highlights
    highlights = response_data.get("highlights")
    if not isinstance(highlights, dict):
        highlights = {"good": [], "bad": []}
    else:
        highlights = {
            "good": highlights.get("good", []) if isinstance(highlights.get("good"), list) else [],
            "bad": highlights.get("bad", []) if isinstance(highlights.get("bad"), list) else [],
        }

    # Validate suggestions
    suggestions = response_data.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []

    return {
        "summary_text": summary_text,
        "highlights": highlights,
        "suggestions": suggestions,
    }


# ── GoalService (async DB operations) ───────────────────────────────────────


class GoalService:
    """Async service for goal CRUD, weekly prompts, and review generation."""

    def __init__(self, session: AsyncSession, api_key: str | None = None):
        self.session = session
        key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=key) if key else None
        self.model = settings.gemini_model

    # ── Goal methods ─────────────────────────────────────────────────────

    async def set_goal(self, target_pnl: Decimal) -> TradingGoal:
        """Set or update monthly profit target.

        Only 1 active goal per month — replaces existing if found.
        """
        month_start = date.today().replace(day=1)

        result = await self.session.execute(
            select(TradingGoal).where(
                TradingGoal.month == month_start,
                TradingGoal.status == "active",
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.target_pnl = target_pnl
            await self.session.flush()
            return existing

        goal = TradingGoal(target_pnl=target_pnl, month=month_start, status="active")
        self.session.add(goal)
        await self.session.flush()
        return goal

    async def get_current_goal(self) -> dict | None:
        """Get current month's goal with computed progress."""
        month_start = date.today().replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)

        result = await self.session.execute(
            select(TradingGoal).where(
                TradingGoal.month == month_start,
                TradingGoal.status == "active",
            )
        )
        goal = result.scalar_one_or_none()
        if not goal:
            return None

        actual_pnl = await self._compute_actual_pnl(month_start, next_month)
        progress = compute_goal_progress(float(actual_pnl), float(goal.target_pnl))

        return {
            "id": goal.id,
            "target_pnl": float(goal.target_pnl),
            "actual_pnl": float(actual_pnl),
            "month": goal.month,
            "status": goal.status,
            "progress_pct": progress["percentage"],
            "progress_color": progress["color"],
            "created_at": goal.created_at,
            "updated_at": goal.updated_at,
        }

    async def get_goal_history(self, page: int = 1, page_size: int = 10) -> dict:
        """Get past goals with computed progress, paginated."""
        offset = (page - 1) * page_size

        # Count total
        count_result = await self.session.execute(
            select(sa_func.count()).select_from(TradingGoal)
        )
        total = count_result.scalar() or 0

        # Fetch page
        result = await self.session.execute(
            select(TradingGoal)
            .order_by(TradingGoal.month.desc())
            .offset(offset)
            .limit(page_size)
        )
        goals = result.scalars().all()

        goal_dicts = []
        for goal in goals:
            if goal.month.month == 12:
                next_month = goal.month.replace(year=goal.month.year + 1, month=1)
            else:
                next_month = goal.month.replace(month=goal.month.month + 1)

            actual_pnl = await self._compute_actual_pnl(goal.month, next_month)
            progress = compute_goal_progress(float(actual_pnl), float(goal.target_pnl))

            goal_dicts.append({
                "id": goal.id,
                "target_pnl": float(goal.target_pnl),
                "actual_pnl": float(actual_pnl),
                "month": goal.month,
                "status": goal.status,
                "progress_pct": progress["percentage"],
                "progress_color": progress["color"],
                "created_at": goal.created_at,
                "updated_at": goal.updated_at,
            })

        return {"goals": goal_dicts, "total": total}

    async def _compute_actual_pnl(self, month_start: date, month_end_exclusive: date) -> Decimal:
        """Sum net_pnl from SELL trades within the given month."""
        result = await self.session.execute(
            select(sa_func.coalesce(sa_func.sum(Trade.net_pnl), 0)).where(
                Trade.side == "SELL",
                Trade.trade_date >= month_start,
                Trade.trade_date < month_end_exclusive,
            )
        )
        return result.scalar() or Decimal("0")

    # ── Weekly prompt methods ────────────────────────────────────────────

    async def get_pending_prompt(self) -> WeeklyPrompt | None:
        """Get the most recent unanswered prompt."""
        result = await self.session.execute(
            select(WeeklyPrompt)
            .where(WeeklyPrompt.response.is_(None))
            .order_by(WeeklyPrompt.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_weekly_prompt(self) -> WeeklyPrompt:
        """Create a new weekly risk tolerance prompt.

        Expires any existing pending prompts first.
        """
        # Expire existing pending prompts
        await self.session.execute(
            update(WeeklyPrompt)
            .where(WeeklyPrompt.response.is_(None))
            .values(response="expired")
        )

        # Get current risk level
        profile_result = await self.session.execute(select(UserRiskProfile).limit(1))
        profile = profile_result.scalar_one_or_none()
        risk_level = profile.risk_level if profile else 3

        # Calculate week_start (Monday of current week)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        prompt = WeeklyPrompt(
            week_start=week_start,
            risk_level_before=risk_level,
        )
        self.session.add(prompt)
        await self.session.flush()
        return prompt

    async def respond_to_prompt(self, prompt_id: int, response: str) -> WeeklyPrompt:
        """Record user's weekly prompt response and update risk level.

        Args:
            prompt_id: ID of the pending prompt.
            response: One of "cautious", "unchanged", "aggressive".

        Raises:
            ValueError: If prompt not found or already answered.
        """
        result = await self.session.execute(
            select(WeeklyPrompt).where(WeeklyPrompt.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise ValueError(f"Prompt {prompt_id} not found")
        if prompt.response is not None:
            raise ValueError(f"Prompt {prompt_id} already answered")

        # Compute delta: -1 cautious, 0 unchanged, +1 aggressive
        delta_map = {"cautious": -1, "unchanged": 0, "aggressive": 1}
        delta = delta_map[response]
        new_level = clamp_risk_level(prompt.risk_level_before or 3, delta)

        # Update prompt
        prompt.response = response
        prompt.risk_level_after = new_level

        # Update user risk profile
        profile_result = await self.session.execute(select(UserRiskProfile).limit(1))
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile.risk_level = new_level

        await self.session.flush()
        return prompt

    # ── Weekly review methods ────────────────────────────────────────────

    async def get_latest_review(self) -> WeeklyReview | None:
        """Get the most recent weekly review."""
        result = await self.session.execute(
            select(WeeklyReview)
            .order_by(WeeklyReview.week_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_review_history(self, page: int = 1, page_size: int = 10) -> dict:
        """Get weekly reviews paginated."""
        offset = (page - 1) * page_size

        count_result = await self.session.execute(
            select(sa_func.count()).select_from(WeeklyReview)
        )
        total = count_result.scalar() or 0

        result = await self.session.execute(
            select(WeeklyReview)
            .order_by(WeeklyReview.week_end.desc())
            .offset(offset)
            .limit(page_size)
        )
        reviews = result.scalars().all()

        return {"reviews": reviews, "total": total}

    async def generate_review(self) -> str:
        """Generate AI weekly performance review via Gemini.

        Gathers week's data, calls Gemini with structured output,
        applies 3-stage fallback (parsed → low-temp retry → manual JSON parse),
        and persists the review.
        """
        today = date.today()
        week_end = today
        week_start = today - timedelta(days=6)

        # Gather week's trades
        trades_result = await self.session.execute(
            select(Trade).where(
                Trade.trade_date >= week_start,
                Trade.trade_date <= week_end,
            )
        )
        trades = trades_result.scalars().all()
        trades_data = [
            {
                "ticker": str(t.ticker_id),  # ticker_id — API layer can resolve to symbol
                "side": t.side,
                "pnl": float(t.net_pnl) if t.net_pnl else 0,
            }
            for t in trades
        ]

        # Trade stats
        trades_count = len(trades)
        win_count = sum(1 for t in trades if t.side == "SELL" and t.net_pnl and t.net_pnl > 0)
        total_pnl = sum(float(t.net_pnl or 0) for t in trades if t.side == "SELL")

        # Gather habit detections (this week's)
        habits_result = await self.session.execute(
            select(HabitDetection).where(
                HabitDetection.detected_at >= week_start,
            )
        )
        habits = habits_result.scalars().all()
        habit_data = [
            {"habit_type": h.habit_type, "ticker": str(h.ticker_id)}
            for h in habits
        ]

        # Gather pick outcomes (this week's)
        picks_result = await self.session.execute(
            select(DailyPick).where(
                DailyPick.pick_date >= week_start,
                DailyPick.pick_date <= week_end,
            )
        )
        picks = picks_result.scalars().all()
        pick_outcomes = [
            {"ticker": str(p.ticker_id), "outcome": p.outcome or "pending"}
            for p in picks
        ]

        # Get current risk level
        profile_result = await self.session.execute(select(UserRiskProfile).limit(1))
        profile = profile_result.scalar_one_or_none()
        risk_level = profile.risk_level if profile else 3

        # Get current goal progress
        goal_progress = None
        current_goal = await self.get_current_goal()
        if current_goal:
            goal_progress = {
                "percentage": current_goal["progress_pct"],
                "color": current_goal["progress_color"],
            }

        # Build prompt and call Gemini
        prompt = build_review_prompt(trades_data, habit_data, pick_outcomes, risk_level, goal_progress)

        review_data = None
        if self.client:
            review_data = await self._call_gemini_review(prompt)

        parsed = parse_review_response(review_data)

        # Persist review
        review = WeeklyReview(
            week_start=week_start,
            week_end=week_end,
            summary_text=parsed["summary_text"],
            highlights=parsed["highlights"],
            suggestions=parsed["suggestions"],
            trades_count=trades_count,
            win_count=win_count,
            total_pnl=Decimal(str(total_pnl)),
        )
        self.session.add(review)
        await self.session.flush()

        logger.info(f"Weekly review generated: {week_start} to {week_end}, {trades_count} trades")
        return parsed["summary_text"]

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=4, max=15),
        retry=retry_if_exception_type(ServerError),
        reraise=True,
    )
    async def _call_gemini_review(self, prompt: str) -> dict | None:
        """Call Gemini API with 3-stage fallback for review generation.

        Stage 1: response.parsed (structured output)
        Stage 2: Low-temperature retry if parsed is None
        Stage 3: Manual JSON parse from response.text
        """
        if not self.client:
            return None

        try:
            # Stage 1: Normal structured output
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=WeeklyReviewOutput,
                    system_instruction=WEEKLY_REVIEW_SYSTEM_INSTRUCTION,
                    temperature=0.7,
                    max_output_tokens=4096,
                ),
            )

            if response.parsed:
                data = response.parsed
                if isinstance(data, WeeklyReviewOutput):
                    return data.model_dump()
                return data if isinstance(data, dict) else None

            # Stage 2: Low-temperature retry
            if response.text:
                logger.warning("Weekly review response.parsed is None, retrying at temp=0.1")
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=WeeklyReviewOutput,
                        system_instruction=WEEKLY_REVIEW_SYSTEM_INSTRUCTION,
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )
                if response.parsed:
                    data = response.parsed
                    if isinstance(data, WeeklyReviewOutput):
                        return data.model_dump()
                    return data if isinstance(data, dict) else None

            # Stage 3: Manual JSON parse
            if response.text:
                logger.warning("Low-temp retry also failed, falling back to manual JSON parse")
                try:
                    return json.loads(response.text)
                except Exception as e:
                    logger.error(f"Manual JSON parse failed: {e}")

        except (ClientError, ServerError) as e:
            logger.error(f"Gemini weekly review API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in weekly review generation: {e}")

        return None
