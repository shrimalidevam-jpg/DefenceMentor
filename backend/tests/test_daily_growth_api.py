"""Daily vocabulary and SSB preparation API tests."""

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
from app.models.daily_vocabulary import DailyVocabularyAttempt
from app.models.enums import UserRole
from app.models.users import User
from app.services.daily_growth import today_vocabulary


class DailyGrowthApiTests(unittest.TestCase):
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
        cls.user_id = uuid4()
        database = cls.session_factory()
        database.add(User(id=cls.user_id, email="daily-growth@example.com", full_name="Daily Student", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT))
        database.commit()
        database.close()
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_five_daily_words_tip_answers_and_score_persist(self) -> None:
        response = self.client.get("/api/daily-growth/today", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["questions"]), 5)
        self.assertEqual(len({question["id"] for question in body["questions"]}), 5)
        self.assertEqual(body["answered_count"], 0)
        self.assertIsNone(body["questions"][0]["explanation"])
        self.assertTrue(body["ssb_tip"])
        self.assertTrue(body["ssb_category"])

        question = today_vocabulary(date.today())[0]
        answer = self.client.post(
            "/api/daily-growth/vocabulary/answer",
            headers=self.headers,
            json={"word_id": question.id, "selected_option": question.correct_option},
        )
        self.assertEqual(answer.status_code, 200)
        self.assertTrue(answer.json()["is_correct"])
        self.assertEqual(answer.json()["meaning"], question.meaning)
        self.assertEqual(answer.json()["answered_count"], 1)

        reloaded = self.client.get("/api/daily-growth/today", headers=self.headers).json()
        answered_question = next(item for item in reloaded["questions"] if item["id"] == question.id)
        self.assertTrue(answered_question["is_correct"])
        self.assertEqual(answered_question["explanation"], question.meaning)
        self.assertEqual(reloaded["correct_count"], 1)

        duplicate = self.client.post(
            "/api/daily-growth/vocabulary/answer",
            headers=self.headers,
            json={"word_id": question.id, "selected_option": question.correct_option},
        )
        self.assertEqual(duplicate.status_code, 409)
        database = self.session_factory()
        self.assertEqual(database.scalar(select(func.count(DailyVocabularyAttempt.id))), 1)
        database.close()


if __name__ == "__main__":
    unittest.main()
