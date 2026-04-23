"""LotMatch model — junction table linking SELL trades to consumed lots.

Records which lots a SELL trade consumed and how many shares from each.
Enables accurate delete reversal: restore lot remaining_quantity on SELL delete.
"""
from sqlalchemy import BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class LotMatch(Base):
    __tablename__ = "lot_matches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sell_trade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False)
    lot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lots.id"), nullable=False)
    matched_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<LotMatch(sell_trade={self.sell_trade_id}, lot={self.lot_id}, qty={self.matched_quantity})>"
