"""Phase 5 knowledge graph traversal tests."""

import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.curriculum import Concept, Prerequisite
from app.services.knowledge_graph import KnowledgeGraphCycleError, build_learning_path


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.database = Session(self.engine)
        self.concepts = [Concept(id=uuid4(), topic_id=uuid4(), name=name) for name in ("Fractions", "Ratios", "Probability")]
        self.database.add_all(self.concepts)
        self.database.flush()
        fractions, ratios, probability = self.concepts
        self.database.add_all([
            Prerequisite(concept_id=ratios.id, prerequisite_concept_id=fractions.id, is_required=True),
            Prerequisite(concept_id=probability.id, prerequisite_concept_id=ratios.id, is_required=True),
        ])
        self.database.commit()

    def tearDown(self) -> None:
        self.database.close()
        self.engine.dispose()

    def test_path_is_prerequisite_first(self) -> None:
        path = build_learning_path(self.database, self.concepts[2].id)
        self.assertEqual([concept.name for concept in path], ["Fractions", "Ratios", "Probability"])

    def test_shared_prerequisite_is_returned_once(self) -> None:
        extra = Concept(id=uuid4(), topic_id=uuid4(), name="Counting")
        self.database.add(extra)
        self.database.flush()
        self.database.add(Prerequisite(concept_id=self.concepts[2].id, prerequisite_concept_id=extra.id, is_required=True))
        self.database.commit()
        path = build_learning_path(self.database, self.concepts[2].id)
        self.assertEqual(len({concept.id for concept in path}), len(path))

    def test_cycle_is_rejected(self) -> None:
        fractions, _, probability = self.concepts
        self.database.add(Prerequisite(concept_id=fractions.id, prerequisite_concept_id=probability.id, is_required=True))
        self.database.commit()
        with self.assertRaises(KnowledgeGraphCycleError):
            build_learning_path(self.database, probability.id)


if __name__ == "__main__":
    unittest.main()
