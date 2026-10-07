"""Phase 10 mastery scoring tests."""

import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.curriculum import Concept
from app.models.enums import Difficulty, QuestionType, UserRole
from app.models.questions import Question, QuestionAttempt
from app.models.users import User
from app.services.mastery_engine import calculate_mastery_score, mastery_summary, update_mastery


class MasteryEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.database = Session(self.engine)
        self.user_id = uuid4()
        self.concept_id = uuid4()
        self.database.add_all([
            User(id=self.user_id, email="mastery@example.com", full_name="Mastery Student", password_hash="hash", role=UserRole.STUDENT),
            Concept(id=self.concept_id, topic_id=uuid4(), name="Algebra"),
        ])
        self.database.commit()

    def tearDown(self) -> None:
        self.database.close()
        self.engine.dispose()

    def test_difficulty_and_recency_affect_mastery(self) -> None:
        easy = Question(id=uuid4(), exam_id=uuid4(), subject_id=uuid4(), concept_id=self.concept_id, prompt="Easy", difficulty=Difficulty.EASY, question_type=QuestionType.MULTIPLE_CHOICE, is_published=True)
        hard = Question(id=uuid4(), exam_id=uuid4(), subject_id=uuid4(), concept_id=self.concept_id, prompt="Hard", difficulty=Difficulty.HARD, question_type=QuestionType.MULTIPLE_CHOICE, is_published=True)
        self.database.add_all([
            easy,
            hard,
            QuestionAttempt(user_id=self.user_id, question_id=easy.id, is_correct=False, attempted_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            QuestionAttempt(user_id=self.user_id, question_id=hard.id, is_correct=True, response_time_seconds=30, confidence=1, attempted_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ])
        self.database.commit()

        score = calculate_mastery_score(self.database, self.user_id, self.concept_id)
        self.assertGreater(score, 50.0)
        self.assertLess(score, 100.0)
        self.assertEqual(update_mastery(self.database, self.user_id, self.concept_id), score)

    def test_summary_reports_learning_evidence(self) -> None:
        question = Question(id=uuid4(), exam_id=uuid4(), subject_id=uuid4(), concept_id=self.concept_id, prompt="Question", difficulty=Difficulty.MEDIUM, question_type=QuestionType.MULTIPLE_CHOICE, is_published=True)
        self.database.add(QuestionAttempt(user_id=self.user_id, question_id=question.id, is_correct=True, response_time_seconds=42, hints_used=2))
        self.database.add(question)
        self.database.commit()

        summary = mastery_summary(self.database, self.user_id, self.concept_id)
        self.assertEqual(summary["attempt_count"], 1)
        self.assertEqual(summary["correct_count"], 1)
        self.assertEqual(summary["accuracy"], 100.0)
        self.assertEqual(summary["hints_used"], 2)


if __name__ == "__main__":
    unittest.main()