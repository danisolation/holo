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
from app.models.price_alert import PriceAlert  # noqa: E402

__all__ = ["Base", "Ticker", "DailyPrice", "Financial", "TechnicalIndicator", "AIAnalysis", "AnalysisType", "NewsArticle", "UserWatchlist", "PriceAlert"]
