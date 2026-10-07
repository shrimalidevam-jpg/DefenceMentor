"""Verified external tutorial resources for school foundations and NDA preparation."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TutorialResource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tutorial_resources"

    board: Mapped[str] = mapped_column(String(40), index=True)
    grade_level: Mapped[int] = mapped_column(Integer, index=True)
    subject: Mapped[str] = mapped_column(String(120), index=True)
    topic: Mapped[str] = mapped_column(String(180), index=True)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    provider: Mapped[str] = mapped_column(String(120))
    resource_type: Mapped[str] = mapped_column(String(40), default="video")
    language: Mapped[str] = mapped_column(String(40), default="English")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[object]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
