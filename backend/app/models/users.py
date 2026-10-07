"""User identity and student-profile persistence models."""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Enum as SqlEnum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, native_enum=False, values_callable=lambda enum_type: [member.value for member in enum_type]),
        default=UserRole.STUDENT,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    profile: Mapped[Optional["StudentProfile"]] = relationship(back_populates="user", uselist=False)


class StudentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    exam_target: Mapped[str] = mapped_column(String(100))
    current_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    learning_preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    academic_stream: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    science_group: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, default=360, nullable=False)
    study_start_time: Mapped[str] = mapped_column(String(5), default="08:00", nullable=False)
    focus_session_minutes: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    planner_setup_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    study_subjects: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    math_share_percent: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    student_phone: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    parent_phone: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    student_photo: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    parent_photo: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    guardian_report_consent_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
