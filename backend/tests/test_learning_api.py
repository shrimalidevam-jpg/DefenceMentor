"""Phase 9 personalized learning flow tests."""

import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import chat as chat_route
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.curriculum import Concept, Prerequisite
from app.models.enums import Difficulty, QuestionType, UserRole
from app.models.questions import Question, QuestionAnswer, QuestionOption
from app.models.users import StudentProfile, User


class LearningApiTests(unittest.TestCase):
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
        cls.user = User(
            id=cls.user_id,
            email="learning@example.com",
            full_name="Learning Student",
            password_hash=hash_password("SecurePass9"),
            role=UserRole.STUDENT,
        )
        database.add_all([cls.user, StudentProfile(user_id=cls.user_id, exam_target="NDA")])
        cls.prerequisite = Concept(id=uuid4(), topic_id=uuid4(), name="Fractions", description="Parts of a whole")
        cls.target = Concept(id=uuid4(), topic_id=uuid4(), name="Probability", description="Likelihood of an event")
        database.add_all([
            cls.prerequisite,
            cls.target,
            Prerequisite(concept_id=cls.target.id, prerequisite_concept_id=cls.prerequisite.id, is_required=True),
        ])
        question = Question(
            id=uuid4(),
            exam_id=uuid4(),
            subject_id=uuid4(),
            concept_id=cls.prerequisite.id,
            prompt="What is 1/2 + 1/2?",
            explanation="The result is one whole.",
            difficulty=Difficulty.EASY,
            question_type=QuestionType.MULTIPLE_CHOICE,
            is_published=True,
        )
        correct = QuestionOption(id=uuid4(), question_id=question.id, text="1", display_order=1)
        database.add_all([question, correct, QuestionAnswer(question_id=question.id, correct_option_id=correct.id)])
        database.commit()
        cls.prerequisite_id = cls.prerequisite.id
        cls.target_id = cls.target.id
        cls.question_id = question.id
        cls.correct_option_id = correct.id
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}
        database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_learning_session_teaches_prerequisite_then_advances(self) -> None:
        response = self.client.post(
            "/api/learning/sessions",
            headers=self.headers,
            json={"target_concept_id": str(self.target_id)},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["current_concept_id"], str(self.prerequisite_id))
        self.assertEqual([item["name"] for item in body["path"]], ["Fractions", "Probability"])

        session_id = body["id"]
        lesson = self.client.get(f"/api/learning/sessions/{session_id}/current/lesson", headers=self.headers)
        self.assertEqual(lesson.status_code, 200)
        self.assertEqual(lesson.json()["concept_id"], str(self.prerequisite_id))

        practice = self.client.get(f"/api/learning/sessions/{session_id}/current/practice", headers=self.headers)
        self.assertEqual(practice.status_code, 200)
        answer = self.client.post(
            f"/api/learning/sessions/{session_id}/questions/{self.question_id}/answer",
            headers=self.headers,
            json={"selected_option_id": str(self.correct_option_id), "activity_type": "understanding_check"},
        )
        self.assertEqual(answer.status_code, 200)
        self.assertTrue(answer.json()["is_correct"])
        self.assertEqual(answer.json()["next_concept_id"], str(self.target_id))

        resumed = self.client.get(f"/api/learning/sessions/{session_id}", headers=self.headers)
        self.assertEqual(resumed.status_code, 200)
        path = resumed.json()["path"]
        self.assertEqual(path[0]["status"], "completed")
        self.assertEqual(resumed.json()["current_concept_id"], str(self.target_id))


if __name__ == "__main__":
    unittest.main()