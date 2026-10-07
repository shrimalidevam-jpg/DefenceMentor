"""Verified source ingestion and retrieval endpoints for Phase 13."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models.content import ContentChunk, ContentDocument, Source
from app.models.users import User
from app.schemas.rag import ContentChunkCreate, RetrievalResponse, RetrievedSource, SourceCreateRequest, SourceCreateResponse
from app.services.rag_retriever import retrieve_chunks


router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/sources", response_model=SourceCreateResponse, status_code=status.HTTP_201_CREATED)
def create_verified_source(
    payload: SourceCreateRequest,
    chunks: list[ContentChunkCreate],
    admin_user: User = Depends(require_admin),
    database: Session = Depends(get_db),
) -> SourceCreateResponse:
    if not chunks:
        raise HTTPException(status_code=422, detail="At least one reviewed content chunk is required")
    source = Source(name=payload.name.strip(), title=payload.title.strip(), source_type=payload.source_type, url=payload.url, is_verified=payload.verified)
    database.add(source)
    database.flush()
    document = ContentDocument(source_id=source.id, subject_id=payload.subject_id, title=payload.title.strip())
    database.add(document)
    database.flush()
    for index, chunk in enumerate(chunks):
        database.add(ContentChunk(document_id=document.id, topic_id=payload.topic_id, chunk_index=index, content=chunk.content.strip(), page_reference=chunk.page_reference))
    database.commit()
    return SourceCreateResponse(source_id=source.id, document_id=document.id, chunk_count=len(chunks), is_verified=source.is_verified)


@router.get("/search", response_model=RetrievalResponse)
def search_verified_sources(
    query: str,
    topic_id: UUID | None = None,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> RetrievalResponse:
    if not query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    bounded_limit = min(max(limit, 1), 10)
    results = [RetrievedSource.model_validate(item) for item in retrieve_chunks(database, query, topic_id, bounded_limit)]
    return RetrievalResponse(query=query, results=results)