"""Persisted daily revision tests based on completed study-plan topics."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DailyReviewAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_review_attempts"

    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    question_count: Mapped[int] = mapped_column(Integer)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[Optional[float]] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "plan_date", "attempt_no", name="uq_daily_review_attempt_user_date_number"),)


class DailyReviewItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_review_items"

    attempt_id: Mapped[object] = mapped_column(ForeignKey("daily_review_attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[object] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    selected_option_id: Mapped[Optional[object]] = mapped_column(ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_daily_review_item_question"),
        UniqueConstraint("attempt_id", "position", name="uq_daily_review_item_position"),
    )
