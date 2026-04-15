"""News articles scraped from CafeF for sentiment analysis.

One row per ticker per article URL (deduplicated via unique constraint).
"""
from datetime import datetime

from sqlalchemy import Integer, BigInteger, String, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class NewsArticle(Base):
    """News article scraped from CafeF for a ticker."""
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="cafef"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "url", name="uq_news_articles_ticker_url"),
        # Index on (ticker_id, published_at DESC) created via migration DDL
    )

    def __repr__(self) -> str:
        return f"<NewsArticle(ticker_id={self.ticker_id}, title={self.title[:40]})>"
