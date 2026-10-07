"""Assessment definitions, attempts and the questions assigned to them."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AttemptStatus


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessments"
    exam_id: Mapped[object] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    assessment_type: Mapped[str] = mapped_column(String(40), default="diagnostic")
    time_limit_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AssessmentAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_attempts"
    assessment_id: Mapped[object] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[AttemptStatus] = mapped_column(
        SqlEnum(AttemptStatus, native_enum=False, values_callable=lambda enum_type: [member.value for member in enum_type]),
        default=AttemptStatus.IN_PROGRESS,
    )
    score: Mapped[Optional[float]] = mapped_column(nullable=True)
    current_round: Mapped[str] = mapped_column(String(30), default="easy")
    current_question_id: Mapped[Optional[object]] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    schedule_type: Mapped[str] = mapped_column(String(20), default="weekly")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    section_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AssessmentQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_questions"
    assessment_id: Mapped[object] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[object] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    round_name: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("assessment_id", "question_id"),)


class AssessmentQuestionAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_question_assignments"
    attempt_id: Mapped[object] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[object] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    section_name: Mapped[str] = mapped_column(String(30), index=True)
    display_order: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_assessment_assignment_attempt_question"),
        UniqueConstraint("attempt_id", "section_name", "display_order", name="uq_assessment_assignment_attempt_section_order"),
    )
