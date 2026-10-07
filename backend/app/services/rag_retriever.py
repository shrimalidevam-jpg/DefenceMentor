"""Deterministic verified-source retrieval for the Phase 13 MVP."""

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import ContentChunk, ContentDocument, Source


STOP_WORDS = {
    "the", "and", "for", "with", "what", "this", "that", "from", "about", "explain",
    "teach", "please", "topic", "chapter", "concept", "can", "you", "help", "me", "how",
    "why", "does", "is", "are", "was", "were", "give", "more", "tell", "show", "derive",
}


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]{2,}", value.casefold()) if term not in STOP_WORDS}


def retrieve_chunks(database: Session, query: str, topic_id: UUID | None = None, limit: int = 5) -> list[dict]:
    query_terms = _terms(query)
    if not query_terms:
        return []
    statement = (
        select(ContentChunk, ContentDocument, Source)
        .join(ContentDocument, ContentDocument.id == ContentChunk.document_id)
        .join(Source, Source.id == ContentDocument.source_id)
        .where(Source.is_verified.is_(True))
    )
    if topic_id is not None:
        statement = statement.where(ContentChunk.topic_id == topic_id)
    matches: list[dict] = []
    for chunk, document, source in database.execute(statement).all():
        content_terms = _terms(chunk.content)
        title_terms = _terms(f"{document.title} {source.title}")
        content_overlap = query_terms.intersection(content_terms)
        title_overlap = query_terms.intersection(title_terms)
        if not content_overlap and not title_overlap:
            continue
        content_score = len(content_overlap) / len(query_terms)
        title_score = len(title_overlap) / len(query_terms)
        score = round(0.65 * content_score + 0.35 * title_score, 4)
        if score < 0.25:
            continue
        matches.append({
            "source_id": source.id,
            "document_id": document.id,
            "source_name": source.name,
            "title": document.title,
            "url": source.url,
            "page_reference": chunk.page_reference,
            "relevance_score": score,
            "content": chunk.content,
        })
    matches.sort(key=lambda item: (-item["relevance_score"], item["title"], item["content"]))
    return matches[:limit]
