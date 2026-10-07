"""Persistent daily SSB guidance and private SSB coaching messages."""

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DailySSBGuidance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_ssb_guidance"
    __table_args__ = (UniqueConstraint("user_id", "guidance_date", name="uq_daily_ssb_guidance_user_date"),)

    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    guidance_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(160))
    guidance: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    reflection_question: Mapped[str] = mapped_column(Text)


class SSBGuidanceMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ssb_guidance_messages"

    user_id: Mapped[object] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
