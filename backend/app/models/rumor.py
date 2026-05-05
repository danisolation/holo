"""Community rumors/posts from Fireant.vn for sentiment analysis.

One row per Fireant post (deduplicated via post_id unique constraint).
"""
from datetime import datetime

from sqlalchemy import (
    Integer, BigInteger, String, Text, Boolean, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class Rumor(Base):
    """Community post scraped from Fireant.vn for a ticker."""
    __tablename__ = "rumors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    post_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_authentic: Mapped[bool] = mapped_column(Boolean, default=False)
    total_likes: Mapped[int] = mapped_column(Integer, default=0)
    total_replies: Mapped[int] = mapped_column(Integer, default=0)
    fireant_sentiment: Mapped[int] = mapped_column(Integer, default=0)
    posted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("post_id", name="uq_rumors_post_id"),
        Index("ix_rumors_ticker_posted", "ticker_id", text("posted_at DESC")),
    )

    def __repr__(self) -> str:
        return f"<Rumor(post_id={self.post_id}, author={self.author_name})>"
