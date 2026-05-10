"""Haber sentiment skoru modeli."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    __table_args__ = (Index("ix_sentiment_lookup", "symbol", "scored_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # cryptopanic
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)  # -1.0 ~ 1.0
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    scored_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return (
            f"<SentimentScore {self.symbol} {self.source} "
            f"score={self.score} at={self.scored_at}>"
        )
