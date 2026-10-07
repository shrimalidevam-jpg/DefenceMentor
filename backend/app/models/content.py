"""Verified educational source metadata and source documents."""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SourceType


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    name: Mapped[str] = mapped_column(String(180))
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[SourceType] = mapped_column(
        SqlEnum(SourceType, native_enum=False, values_callable=lambda enum_type: [member.value for member in enum_type])
    )
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    published_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class ContentDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_documents"
    source_id: Mapped[object] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[Optional[object]] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class ContentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_chunks"
    document_id: Mapped[object] = mapped_column(ForeignKey("content_documents.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[Optional[object]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
