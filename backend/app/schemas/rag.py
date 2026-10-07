"""API contracts for verified Phase 13 retrieval."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import SourceType


class SourceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    title: str = Field(min_length=2, max_length=255)
    source_type: SourceType
    url: str | None = Field(default=None, max_length=2048)
    subject_id: UUID | None = None
    topic_id: UUID | None = None
    verified: bool = False


class ContentChunkCreate(BaseModel):
    content: str = Field(min_length=20, max_length=20000)
    page_reference: str | None = Field(default=None, max_length=100)


class SourceCreateResponse(BaseModel):
    source_id: UUID
    document_id: UUID
    chunk_count: int
    is_verified: bool


class RetrievedSource(BaseModel):
    source_id: UUID
    document_id: UUID
    source_name: str
    title: str
    url: str | None
    page_reference: str | None
    relevance_score: float
    content: str


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievedSource]