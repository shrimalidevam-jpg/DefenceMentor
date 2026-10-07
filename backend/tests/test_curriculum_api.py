"""Phase 4 curriculum hierarchy API tests."""

import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.curriculum import Chapter, Concept, Exam, Prerequisite, Subject, Topic


class CurriculumApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False)

        def override_database():
            database = cls.session_factory()
            try:
                yield database
            finally:
                database.close()

        app.dependency_overrides[get_db] = override_database
        cls.client = TestClient(app)

        database = cls.session_factory()
        exam_id = uuid4()
        subject_id = uuid4()
        chapter_id = uuid4()
        topic_id = uuid4()
        prerequisite_concept_id = uuid4()
        concept_id = uuid4()
        exam = Exam(id=exam_id, name="NDA", code="NDA", description="Test exam")
        subject = Subject(id=subject_id, exam_id=exam_id, name="Mathematics", code="MATH", display_order=1)
        chapter = Chapter(id=chapter_id, subject_id=subject_id, name="Algebra", display_order=1)
        topic = Topic(id=topic_id, chapter_id=chapter_id, name="Equations", display_order=1)
        prerequisite_concept = Concept(id=prerequisite_concept_id, topic_id=topic_id, name="Basic operations", display_order=1)
        concept = Concept(id=concept_id, topic_id=topic_id, name="Linear equations", display_order=2)
        prerequisite = Prerequisite(
            concept_id=concept_id,
            prerequisite_concept_id=prerequisite_concept_id,
            is_required=True,
        )
        database.add_all([exam, subject, chapter, topic, prerequisite_concept, concept, prerequisite])
        database.commit()
        cls.exam_id = exam.id
        cls.subject_id = subject.id
        cls.chapter_id = chapter.id
        cls.topic_id = topic.id
        cls.concept_id = concept.id
        cls.prerequisite_id = prerequisite.id
        database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_curriculum_hierarchy_and_prerequisites(self) -> None:
        self.assertEqual(self.client.get("/api/curriculum/exams").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/curriculum/exams/{self.exam_id}/subjects").json()[0]["code"],
            "MATH",
        )
        self.assertEqual(
            self.client.get(f"/api/curriculum/subjects/{self.subject_id}/chapters").json()[0]["name"],
            "Algebra",
        )
        self.assertEqual(
            self.client.get(f"/api/curriculum/chapters/{self.chapter_id}/topics").json()[0]["name"],
            "Equations",
        )
        self.assertEqual(
            self.client.get(f"/api/curriculum/topics/{self.topic_id}/concepts").json()[1]["name"],
            "Linear equations",
        )
        prerequisites = self.client.get(
            f"/api/curriculum/concepts/{self.concept_id}/prerequisites"
        )
        self.assertEqual(prerequisites.status_code, 200)
        self.assertEqual(prerequisites.json()[0]["is_required"], True)

    def test_learning_path_returns_target_after_prerequisites(self) -> None:
        response = self.client.get(f"/api/curriculum/concepts/{self.concept_id}/learning-path")
        self.assertEqual(response.status_code, 200)
        path = response.json()
        self.assertEqual([item["concept"]["name"] for item in path], ["Basic operations", "Linear equations"])
        self.assertFalse(path[0]["is_target"])
        self.assertTrue(path[-1]["is_target"])

    def test_missing_curriculum_parent_returns_not_found(self) -> None:
        response = self.client.get(f"/api/curriculum/exams/{uuid4()}/subjects")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
