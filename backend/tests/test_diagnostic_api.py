"""Phase 8 diagnostic engine tests."""

import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import chat as chat_route
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.curriculum import Concept, Prerequisite
from app.models.enums import Difficulty, QuestionType, UserRole
from app.models.questions import Question, QuestionAnswer, QuestionOption, QuestionAttempt
from app.models.users import StudentProfile, User


class DiagnosticApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False)

        def override_database():
            database = cls.session_factory()
            try:
                yield database
            finally:
                database.close()

        app.dependency_overrides[get_db] = override_database
        chat_route.SessionLocal = cls.session_factory
        cls.client = TestClient(app)
        database = cls.session_factory()
        cls.user_id = uuid4()
        cls.user = User(id=cls.user_id, email="diagnostic@example.com", full_name="Diagnostic Student", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT)
        database.add(cls.user)
        database.add(StudentProfile(user_id=cls.user_id, exam_target="NDA"))
        prerequisite = Concept(id=uuid4(), topic_id=uuid4(), name="Fractions")
        target = Concept(id=uuid4(), topic_id=uuid4(), name="Probability")
        database.add_all([prerequisite, target])
        database.add(Prerequisite(concept_id=target.id, prerequisite_concept_id=prerequisite.id, is_required=True))
        cls.correct_option_id = uuid4()
        question_id = uuid4()
        question = Question(id=question_id, exam_id=uuid4(), subject_id=uuid4(), concept_id=prerequisite.id, prompt="What is 1/2 + 1/2?", explanation="The result is one whole.", difficulty=Difficulty.EASY, question_type=QuestionType.MULTIPLE_CHOICE, is_published=True)
        correct = QuestionOption(id=cls.correct_option_id, question_id=question_id, text="1", display_order=1)
        wrong = QuestionOption(id=uuid4(), question_id=question_id, text="1/2", display_order=2)
        database.add_all([question, correct, wrong, QuestionAnswer(question_id=question_id, correct_option_id=cls.correct_option_id)])
        database.commit()
        cls.target_id = target.id
        cls.prerequisite_id = prerequisite.id
        cls.question_id = question_id
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}
        database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_start_diagnostic_returns_prerequisite_questions(self) -> None:
        response = self.client.post(f"/api/diagnostics/concepts/{self.target_id}/start", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["question_count"], 1)
        self.assertEqual(response.json()["questions"][0]["concept_id"], str(self.prerequisite_id))
        self.assertEqual(len(response.json()["questions"][0]["options"]), 2)

    def test_answer_updates_attempt_and_mastery(self) -> None:
        response = self.client.post(
            f"/api/diagnostics/questions/{self.question_id}/answer",
            headers=self.headers,
            json={"selected_option_id": str(self.correct_option_id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_correct"])
        self.assertEqual(response.json()["mastery_score"], 100.0)
        database = self.session_factory()
        self.assertEqual(database.scalar(select(QuestionAttempt).where(QuestionAttempt.question_id == self.question_id)).is_correct, True)
        database.close()

    def test_missing_question_bank_is_explicit(self) -> None:
        response = self.client.post(f"/api/diagnostics/concepts/{uuid4()}/start", headers=self.headers)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
