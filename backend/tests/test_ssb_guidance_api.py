"""SSB guidance and dedicated coaching chat API tests."""

import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.enums import UserRole
from app.models.ssb_guidance import DailySSBGuidance, SSBGuidanceMessage
from app.models.users import User
from app.services.ai_provider import AIProviderUnavailable


class FakeSSBProvider:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, object]]] = []

    def generate(self, messages: list[dict[str, object]]) -> str:
        self.calls.append(messages)
        if "daily coaching card" in str(messages[0]["content"]):
            return json.dumps({
                "title": "Practise responsibility",
                "guidance": "Follow through on a commitment without waiting to be reminded.",
                "action": "Choose one unfinished task and complete it today.",
                "reflection_question": "What helped you finish it?",
            })
        return "Make one honest example and explain what you learned from it."


class SSBGuidanceApiTests(unittest.TestCase):
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
        database.add(User(
            id=cls.user_id,
            email="ssb-guidance@example.com",
            full_name="SSB Student",
            password_hash=hash_password("SecurePass9"),
            role=UserRole.STUDENT,
        ))
        database.commit()
        database.close()
        access_token = create_access_token(str(cls.user_id), UserRole.STUDENT.value)
        cls.headers = {"Authorization": f"Bearer {access_token}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def setUp(self) -> None:
        self.provider = FakeSSBProvider()

    def test_daily_guidance_is_generated_once_and_saved_for_the_day(self) -> None:
        with patch("app.api.routes.ssb_guidance.get_ai_provider", return_value=self.provider):
            first = self.client.get("/api/ssb-guidance/today", headers=self.headers)
            second = self.client.get("/api/ssb-guidance/today", headers=self.headers)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["title"], "Practise responsibility")
        self.assertEqual(first.json()["action"], "Choose one unfinished task and complete it today.")
        self.assertEqual(second.json(), first.json())
        self.assertEqual(len(self.provider.calls), 1)
        database = self.session_factory()
        self.assertEqual(database.scalar(select(func.count(DailySSBGuidance.id))), 1)
        database.close()

    def test_ssb_chat_answers_and_persists_private_conversation_history(self) -> None:
        with patch("app.api.routes.ssb_guidance.get_ai_provider", return_value=self.provider):
            response = self.client.post(
                "/api/ssb-guidance/chat",
                headers=self.headers,
                json={"content": "How can I improve my interview confidence?"},
            )
            history = self.client.get("/api/ssb-guidance/chat", headers=self.headers)

        self.assertEqual(response.status_code, 201)
        self.assertEqual([message["role"] for message in response.json()], ["user", "assistant"])
        self.assertIn("honest example", response.json()[1]["content"])
        self.assertEqual(history.status_code, 200)
        self.assertEqual([message["role"] for message in history.json()["messages"]], ["user", "assistant"])
        self.assertEqual(history.json()["messages"][0]["content"], "How can I improve my interview confidence?")
        database = self.session_factory()
        self.assertEqual(database.scalar(select(func.count(SSBGuidanceMessage.id))), 2)
        database.close()

    def test_ssb_guidance_requires_authentication(self) -> None:
        response = self.client.get("/api/ssb-guidance/today")
        self.assertEqual(response.status_code, 401)

    def test_ssb_chat_reports_unconfigured_ai_provider(self) -> None:
        with patch(
            "app.api.routes.ssb_guidance.get_ai_provider",
            side_effect=AIProviderUnavailable("AI provider is not configured"),
        ):
            response = self.client.post(
                "/api/ssb-guidance/chat",
                headers=self.headers,
                json={"content": "How do I prepare for the SSB interview?"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("AI provider is not configured", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
