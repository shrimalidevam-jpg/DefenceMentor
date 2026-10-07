"""Daily revision tests are scoped to completed study-plan topics."""

import unittest
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.curriculum import Chapter, Concept, Exam, Subject, Topic
from app.models.daily_review import DailyReviewAttempt
from app.models.enums import Difficulty, QuestionType, UserRole
from app.models.questions import Question, QuestionAnswer, QuestionAttempt, QuestionOption
from app.models.study_planner import StudyPlanTask
from app.models.users import StudentProfile, User


class DailyReviewApiTests(unittest.TestCase):
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
        cls.client = TestClient(app)
        database = cls.session_factory()
        cls.user_id = uuid4()
        exam = Exam(id=uuid4(), name="Daily Review Exam", code="NDA")
        subject = Subject(id=uuid4(), exam_id=exam.id, name="Mathematics", code="MATH")
        chapter = Chapter(id=uuid4(), subject_id=subject.id, name="Probability")
        topic = Topic(id=uuid4(), chapter_id=chapter.id, name="Basic Probability")
        concept = Concept(id=uuid4(), topic_id=topic.id, name="Probability basics")
        database.add_all([
            User(id=cls.user_id, email="daily-review@example.com", full_name="Review Student", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT),
            StudentProfile(user_id=cls.user_id, exam_target="NDA"), exam, subject, chapter, topic, concept,
        ])
        database.flush()
        database.add(StudyPlanTask(user_id=cls.user_id, plan_date=date.today(), concept_id=concept.id, task_type="learn", estimated_minutes=25, display_order=1, is_completed=True))
        cls.correct_options = []
        for index in range(3):
            question = Question(
                id=uuid4(), exam_id=exam.id, subject_id=subject.id, chapter_id=chapter.id,
                topic_id=topic.id, concept_id=concept.id, prompt=f"Review question {index + 1}?",
                explanation=f"Explanation {index + 1}", difficulty=Difficulty.EASY,
                question_type=QuestionType.MULTIPLE_CHOICE, is_published=True,
            )
            correct = QuestionOption(id=uuid4(), question_id=question.id, text=f"Correct {index + 1}", display_order=1)
            incorrect = QuestionOption(id=uuid4(), question_id=question.id, text=f"Incorrect {index + 1}", display_order=2)
            database.add_all([question, correct, incorrect, QuestionAnswer(question_id=question.id, correct_option_id=correct.id)])
            cls.correct_options.append((correct.id, incorrect.id))
        database.commit()
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}
        database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_review_uses_completed_topics_and_persists_score(self) -> None:
        started = self.client.post("/api/daily-review/today/start", headers=self.headers)
        self.assertEqual(started.status_code, 201)
        body = started.json()
        self.assertEqual(body["question_count"], 3)
        self.assertEqual(body["question"]["prompt"], "Review question 1?")

        for index in range(3):
            current = body["question"]
            correct_id, incorrect_id = self.correct_options[index]
            chosen_id = str(correct_id if index < 2 else incorrect_id)
            response = self.client.post(
                f"/api/daily-review/{body['id']}/answer",
                headers=self.headers,
                json={"question_id": current["id"], "selected_option_id": chosen_id},
            )
            self.assertEqual(response.status_code, 200)
            answer = response.json()
            self.assertEqual(answer["is_correct"], index < 2)
            self.assertEqual(answer["explanation"], f"Explanation {index + 1}")
            if index < 2:
                self.assertFalse(answer["completed"])
                body["question"] = answer["next_question"]
            else:
                self.assertTrue(answer["completed"])
                self.assertAlmostEqual(answer["score"], 66.67)

        resumed = self.client.post("/api/daily-review/today/start", headers=self.headers)
        self.assertEqual(resumed.status_code, 201)
        self.assertEqual(resumed.json()["status"], "completed")
        self.assertEqual(resumed.json()["correct_answers"], 2)

        database = self.session_factory()
        self.assertEqual(database.scalar(select(DailyReviewAttempt).where(DailyReviewAttempt.user_id == self.user_id)).answered_count, 3)
        self.assertEqual(database.scalar(select(func.count(QuestionAttempt.id)).where(QuestionAttempt.user_id == self.user_id)), 3)
        database.close()


if __name__ == "__main__":
    unittest.main()
