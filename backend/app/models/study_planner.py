"""Persisted daily study-plan tasks generated from student mastery evidence."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudyPlanTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "study_plan_tasks"

    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    concept_id: Mapped[object] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(30))
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=25)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "plan_date", "concept_id", "task_type"),)
