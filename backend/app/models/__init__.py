from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic can detect them
from app.models.ticker import Ticker  # noqa: E402
from app.models.daily_price import DailyPrice  # noqa: E402
from app.models.financial import Financial  # noqa: E402
from app.models.technical_indicator import TechnicalIndicator  # noqa: E402
from app.models.ai_analysis import AIAnalysis, AnalysisType  # noqa: E402
from app.models.news_article import NewsArticle  # noqa: E402
from app.models.user_watchlist import UserWatchlist  # noqa: E402
from app.models.job_execution import JobExecution  # noqa: E402
from app.models.failed_job import FailedJob  # noqa: E402
from app.models.gemini_usage import GeminiUsage  # noqa: E402
from app.models.daily_pick import DailyPick, PickStatus  # noqa: E402
from app.models.user_risk_profile import UserRiskProfile  # noqa: E402
from app.models.trade import Trade  # noqa: E402
from app.models.lot import Lot  # noqa: E402
from app.models.lot_match import LotMatch  # noqa: E402
from app.models.behavior_event import BehaviorEvent  # noqa: E402
from app.models.habit_detection import HabitDetection  # noqa: E402
from app.models.risk_suggestion import RiskSuggestion  # noqa: E402
from app.models.sector_preference import SectorPreference  # noqa: E402
from app.models.trading_goal import TradingGoal  # noqa: E402
from app.models.weekly_prompt import WeeklyPrompt  # noqa: E402
from app.models.weekly_review import WeeklyReview  # noqa: E402
from app.models.discovery_result import DiscoveryResult  # noqa: E402

__all__ = ["Base", "Ticker", "DailyPrice", "Financial", "TechnicalIndicator", "AIAnalysis", "AnalysisType", "NewsArticle", "UserWatchlist", "JobExecution", "FailedJob", "GeminiUsage", "DailyPick", "PickStatus", "UserRiskProfile", "Trade", "Lot", "LotMatch", "BehaviorEvent", "HabitDetection", "RiskSuggestion", "SectorPreference", "TradingGoal", "WeeklyPrompt", "WeeklyReview", "DiscoveryResult"]
