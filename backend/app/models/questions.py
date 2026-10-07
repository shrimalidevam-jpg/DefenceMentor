"""Question bank, answers and student attempts."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Difficulty, QuestionType


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "questions"
    exam_id: Mapped[object] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[object] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[Optional[object]] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    topic_id: Mapped[Optional[object]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    concept_id: Mapped[Optional[object]] = mapped_column(ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    prompt: Mapped[str] = mapped_column("question_text", Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[Difficulty] = mapped_column(
        SqlEnum(Difficulty, native_enum=False, values_callable=lambda enum_type: [member.value for member in enum_type]),
        index=True,
    )
    question_type: Mapped[QuestionType] = mapped_column(
        SqlEnum(QuestionType, native_enum=False, values_callable=lambda enum_type: [member.value for member in enum_type])
    )
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)


class QuestionOption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_options"
    question_id: Mapped[object] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column("option_text", Text)
    display_order: Mapped[int] = mapped_column("position", Integer, default=0)


class QuestionAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_answers"
    question_id: Mapped[object] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    correct_option_id: Mapped[Optional[object]] = mapped_column(ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True)
    correct_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class QuestionAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "question_attempts"
    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[object] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    selected_option_id: Mapped[Optional[object]] = mapped_column(ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    assessment_attempt_id: Mapped[Optional[object]] = mapped_column(ForeignKey("assessment_attempts.id", ondelete="SET NULL"), nullable=True, index=True)
    assessment_round: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
