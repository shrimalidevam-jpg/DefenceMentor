"""Phase 13 verified-source retrieval tests."""

import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.content import ContentChunk, ContentDocument, Source
from app.models.enums import SourceType
from app.services.rag_retriever import retrieve_chunks


class RagRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.database = Session(self.engine)
        verified = Source(id=uuid4(), name="NCERT", title="Probability basics", source_type=SourceType.TEXTBOOK, is_verified=True)
        unverified = Source(id=uuid4(), name="Unknown blog", title="Unreviewed probability", source_type=SourceType.CURATED, is_verified=False)
        verified_document = ContentDocument(id=uuid4(), source_id=verified.id, title=verified.title)
        unverified_document = ContentDocument(id=uuid4(), source_id=unverified.id, title=unverified.title)
        self.database.add_all([
            verified,
            unverified,
            verified_document,
            unverified_document,
            ContentChunk(document_id=verified_document.id, chunk_index=0, content="Probability is the ratio of favourable outcomes to equally likely total outcomes.", page_reference="p. 12"),
            ContentChunk(document_id=unverified_document.id, chunk_index=0, content="Probability is always guessed from a random internet article.", page_reference="p. 1"),
        ])
        self.database.commit()

    def tearDown(self) -> None:
        self.database.close()
        self.engine.dispose()

    def test_retrieval_only_returns_verified_sources(self) -> None:
        results = retrieve_chunks(self.database, "What is probability and favourable outcomes?")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_name"], "NCERT")
        self.assertEqual(results[0]["page_reference"], "p. 12")


if __name__ == "__main__":
    unittest.main()