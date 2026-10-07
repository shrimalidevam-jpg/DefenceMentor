"""Learning-session, mastery and progress tables."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LearningSessionStatus


class StudentMastery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_mastery"
    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[object] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column("mastery_score", Numeric(5, 2), default=0)
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "concept_id"),)


class LearningSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_sessions"
    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[Optional[object]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    target_concept_id: Mapped[object] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    current_concept_id: Mapped[Optional[object]] = mapped_column(ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[LearningSessionStatus] = mapped_column(
        SqlEnum(LearningSessionStatus, native_enum=False, values_callable=lambda enum_type: [member.value for member in enum_type]),
        default=LearningSessionStatus.ACTIVE,
    )
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningProgress(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_progress"
    session_id: Mapped[object] = mapped_column(ForeignKey("learning_sessions.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[object] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="not_started")
    completion_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    __table_args__ = (UniqueConstraint("session_id", "concept_id"),)
