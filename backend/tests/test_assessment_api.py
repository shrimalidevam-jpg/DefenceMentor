"""Phase 11 adaptive assessment API tests."""

import unittest
from datetime import timedelta
from uuid import UUID, uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import chat as chat_route
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.curriculum import Exam, Subject
from app.models.enums import Difficulty, QuestionType, UserRole
from app.models.questions import Question, QuestionAnswer, QuestionOption
from app.models.users import User
from app.services.adaptive_exam_engine import NDA_SECTION_TIME_SECONDS, difficulty_for_performance
from app.services.ai_question_generator import GeneratedQuestion
from app.services.ai_provider import AIProviderUnavailable


class AssessmentApiTests(unittest.TestCase):
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
        cls.exam_id = uuid4()
        cls.user = User(id=cls.user_id, email="assessment@example.com", full_name="Assessment Student", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT)
        math_subject = Subject(id=uuid4(), exam_id=cls.exam_id, name="Mathematics", code="MATH", display_order=1)
        gat_subject = Subject(id=uuid4(), exam_id=cls.exam_id, name="General Ability Test", code="GAT", display_order=2)
        database.add_all([cls.user, Exam(id=cls.exam_id, name="NDA Assessment Exam", code="NDA-TEST"), math_subject, gat_subject])
        database.flush()
        for subject, count in ((math_subject, 120), (gat_subject, 150)):
            for index in range(count):
                question = Question(id=uuid4(), exam_id=cls.exam_id, subject_id=subject.id, prompt=f"{subject.code} question {index}", difficulty=Difficulty.MEDIUM, question_type=QuestionType.MULTIPLE_CHOICE, is_published=True)
                choices = [QuestionOption(id=uuid4(), question_id=question.id, text=f"Answer {position}", display_order=position) for position in range(1, 5)]
                database.add_all([question, *choices, QuestionAnswer(question_id=question.id, correct_option_id=choices[0].id)])
        database.commit()
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}
        database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_performance_thresholds_are_configurable(self) -> None:
        self.assertEqual(difficulty_for_performance(0.9), "hard")
        self.assertEqual(difficulty_for_performance(0.6), "medium")
        self.assertEqual(difficulty_for_performance(0.4), "easy")

    def answer_current_question(self, attempt_id: str, is_correct: bool):
        current = self.client.get(f"/api/assessments/{attempt_id}", headers=self.headers).json()
        question = current["question"]
        self.assertEqual(len(question["options"]), 4)
        expected_text = "Answer 1" if is_correct else "Answer 2"
        selected = next(option for option in question["options"] if option["text"] == expected_text)
        if question["question_number"] == question["total_questions"] and question["round_name"] == "MATH":
            return self.client.post(
                f"/api/assessments/{attempt_id}/finish-section",
                headers=self.headers,
                json={"current_question_id": question["id"], "selected_option_id": selected["id"]},
            )
        if question["question_number"] == question["total_questions"]:
            return self.client.post(
                f"/api/assessments/{attempt_id}/submit",
                headers=self.headers,
                json={"current_question_id": question["id"], "selected_option_id": selected["id"]},
            )
        return self.client.post(
            f"/api/assessments/{attempt_id}/navigate",
            headers=self.headers,
            json={
                "current_question_id": question["id"],
                "selected_option_id": selected["id"],
                "target_question_number": question["question_number"] + 1,
            },
        )

    def test_weekly_mock_has_two_timed_sections_and_negative_marking(self) -> None:
        response = self.client.post("/api/assessments/start", headers=self.headers, json={"exam_id": str(self.exam_id)})
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["current_round"], "MATH")
        self.assertEqual(body["total_exam_questions"], 100)
        self.assertEqual(body["section_time_limit_seconds"], NDA_SECTION_TIME_SECONDS["weekly"])
        self.assertEqual(body["question"]["total_questions"], 50)
        self.assertEqual(body["question"]["question_number"], 1)
        attempt_id = body["id"]

        for question_number in range(50):
            answer = self.answer_current_question(attempt_id, is_correct=question_number != 0)
            self.assertEqual(answer.status_code, 200)
        current = self.client.get(f"/api/assessments/{attempt_id}", headers=self.headers).json()
        self.assertEqual(current["current_round"], "GAT")
        self.assertEqual(current["question"]["total_questions"], 50)
        self.assertEqual(current["question"]["question_number"], 1)

        for _ in range(50):
            answer = self.answer_current_question(attempt_id, is_correct=True)
            self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["status"], "completed")
        report = self.client.get(f"/api/assessments/{attempt_id}/report", headers=self.headers).json()
        self.assertEqual(report["total_questions"], 100)
        self.assertEqual(report["correct_answers"], 99)
        self.assertEqual(report["maximum_marks"], 325)
        self.assertAlmostEqual(report["net_marks"], 321.67, places=2)
        self.assertAlmostEqual(report["score"], (321.6666666667 / 325) * 100, places=2)

    def test_skip_exam_abandons_attempt_without_score_or_report(self) -> None:
        started = self.client.post(
            "/api/assessments/start",
            headers=self.headers,
            json={"exam_id": str(self.exam_id)},
        )
        self.assertEqual(started.status_code, 201)
        attempt_id = started.json()["id"]

        abandoned = self.client.post(
            f"/api/assessments/{attempt_id}/abandon",
            headers=self.headers,
        )
        self.assertEqual(abandoned.status_code, 200)
        self.assertEqual(abandoned.json()["status"], "abandoned")
        self.assertIsNone(abandoned.json()["score"])
        self.assertIsNone(abandoned.json()["question"])

        report = self.client.get(
            f"/api/assessments/{attempt_id}/report",
            headers=self.headers,
        )
        self.assertEqual(report.status_code, 409)

        history = self.client.get(
            f"/api/assessments/history?exam_id={self.exam_id}",
            headers=self.headers,
        )
        abandoned_history = next(item for item in history.json()["history"] if item["id"] == attempt_id)
        self.assertEqual(abandoned_history["status"], "abandoned")
        self.assertIsNone(abandoned_history["score"])

    def test_expired_math_section_moves_to_gat_and_monthly_counts_are_full_length(self) -> None:
        started = self.client.post(
            "/api/assessments/start",
            headers=self.headers,
            json={"exam_id": str(self.exam_id), "schedule_type": "monthly"},
        )
        self.assertEqual(started.status_code, 201)
        body = started.json()
        self.assertEqual(body["total_exam_questions"], 270)
        self.assertEqual(body["question"]["total_questions"], 120)

        from app.models.assessment import AssessmentAttempt

        database = self.session_factory()
        attempt = database.get(AssessmentAttempt, UUID(body["id"]))
        attempt.section_started_at -= timedelta(seconds=NDA_SECTION_TIME_SECONDS["monthly"] + 1)
        database.commit()
        database.close()

        refreshed = self.client.get(f"/api/assessments/{body['id']}", headers=self.headers).json()
        self.assertEqual(refreshed["current_round"], "GAT_PENDING")
        self.assertTrue(refreshed["section_completed"])
        started_gat = self.client.post(f"/api/assessments/{body['id']}/start-gat", headers=self.headers)
        self.assertEqual(started_gat.status_code, 200)
        gat = started_gat.json()
        self.assertEqual(gat["current_round"], "GAT")
        self.assertEqual(gat["question"]["question_number"], 1)
        self.assertEqual(gat["question"]["total_questions"], 150)
        self.assertEqual(gat["section_time_limit_seconds"], NDA_SECTION_TIME_SECONDS["monthly"])

    def test_previous_next_preserve_selected_answers_and_allow_skipping(self) -> None:
        started = self.client.post(
            "/api/assessments/start",
            headers=self.headers,
            json={"exam_id": str(self.exam_id)},
        ).json()
        first = started["question"]
        selected = first["options"][0]["id"]

        second = self.client.post(
            f"/api/assessments/{started['id']}/navigate",
            headers=self.headers,
            json={
                "current_question_id": first["id"],
                "selected_option_id": selected,
                "target_question_number": 2,
            },
        ).json()["question"]
        self.assertEqual(second["question_number"], 2)

        returned = self.client.post(
            f"/api/assessments/{started['id']}/navigate",
            headers=self.headers,
            json={
                "current_question_id": second["id"],
                "selected_option_id": None,
                "target_question_number": 1,
            },
        ).json()["question"]
        self.assertEqual(returned["id"], first["id"])
        self.assertEqual(returned["selected_option_id"], selected)

        skipped = self.client.post(
            f"/api/assessments/{started['id']}/navigate",
            headers=self.headers,
            json={
                "current_question_id": returned["id"],
                "selected_option_id": None,
                "target_question_number": 3,
            },
        )
        self.assertEqual(skipped.status_code, 200)
        self.assertEqual(skipped.json()["question"]["question_number"], 3)

    def test_monthly_attempt_expires_after_its_start_day(self) -> None:
        started = self.client.post(
            "/api/assessments/start",
            headers=self.headers,
            json={"exam_id": str(self.exam_id), "schedule_type": "monthly"},
        ).json()
        from app.models.assessment import AssessmentAttempt

        database = self.session_factory()
        attempt = database.get(AssessmentAttempt, UUID(started["id"]))
        attempt.started_at -= timedelta(days=1)
        database.commit()
        database.close()

        expired = self.client.get(f"/api/assessments/{started['id']}", headers=self.headers)
        self.assertEqual(expired.status_code, 410)
        self.assertIn("same day", expired.json()["detail"])

    def test_short_bank_generates_labeled_four_option_questions(self) -> None:
        exam_id = uuid4()
        database = self.session_factory()
        database.add_all([
            Exam(id=exam_id, name="Generated NDA Exam", code="NDA-GENERATED"),
            Subject(id=uuid4(), exam_id=exam_id, name="Mathematics", code="MATH", display_order=1),
            Subject(id=uuid4(), exam_id=exam_id, name="General Ability Test", code="GAT", display_order=2),
        ])
        database.commit()
        database.close()
        generated = [
            GeneratedQuestion(
                prompt=f"Generated question {index}",
                options=["one", "two", "three", "four"],
                correct_option_index=0,
                explanation="The first choice is correct.",
                difficulty="medium",
                topic="Algebra",
            )
            for index in range(5)
        ]
        with patch("app.api.routes.assessment.generate_question_batch", return_value=generated):
            response = self.client.post(
                "/api/assessments/start",
                headers=self.headers,
                json={"exam_id": str(exam_id)},
            )

        self.assertEqual(response.status_code, 201)
        question = response.json()["question"]
        self.assertTrue(question["is_ai_generated"])
        self.assertEqual(len(question["options"]), 4)

    def test_short_bank_reports_ai_provider_failure(self) -> None:
        exam_id = uuid4()
        database = self.session_factory()
        database.add_all([
            Exam(id=exam_id, name="Unavailable AI Exam", code="NDA-NO-AI"),
            Subject(id=uuid4(), exam_id=exam_id, name="Mathematics", code="MATH", display_order=1),
            Subject(id=uuid4(), exam_id=exam_id, name="General Ability Test", code="GAT", display_order=2),
        ])
        database.commit()
        database.close()
        with patch(
            "app.api.routes.assessment.generate_question_batch",
            side_effect=AIProviderUnavailable("AI provider is not configured"),
        ):
            response = self.client.post(
                "/api/assessments/start",
                headers=self.headers,
                json={"exam_id": str(exam_id)},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("AI generation failed", response.json()["detail"])

    def test_monthly_mock_frequency_is_saved_and_history_has_guidance(self) -> None:
        started = self.client.post(
            "/api/assessments/start",
            headers=self.headers,
            json={"exam_id": str(self.exam_id), "schedule_type": "monthly"},
        )
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.json()["schedule_type"], "monthly")

        history = self.client.get(
            f"/api/assessments/history?exam_id={self.exam_id}",
            headers=self.headers,
        )
        self.assertEqual(history.status_code, 200)
        body = history.json()
        self.assertGreaterEqual(body["total_attempts"], 1)
        self.assertTrue(any(item["schedule_type"] == "monthly" for item in body["history"]))
        self.assertTrue(body["monthly_due"])
        self.assertIsNone(body["average_score"])
        self.assertIn("Complete your first mock test", body["recommendations"][0])


if __name__ == "__main__":
    unittest.main()