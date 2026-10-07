"""Per-student answers to the daily vocabulary practice set."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DailyVocabularyAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_vocabulary_attempts"

    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    practice_date: Mapped[date] = mapped_column(Date, index=True)
    word_id: Mapped[str] = mapped_column(String(60))
    selected_option: Mapped[str] = mapped_column(String(1))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "practice_date", "word_id", name="uq_daily_vocab_user_date_word"),)
