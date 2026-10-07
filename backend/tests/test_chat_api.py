"""Phase 6 authenticated chat API tests."""

import base64
from io import BytesIO
import unittest
from uuid import uuid4
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.api.routes import chat as chat_route
from app.models.base import Base
from app.models.enums import UserRole
from app.models.users import StudentProfile, User
from app.services.ai_provider import AIProviderQuotaExceeded, DisabledAIProvider


class ChatApiTests(unittest.TestCase):
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
        cls.other_user_id = uuid4()
        cls.user = User(id=cls.user_id, email="chat-one@example.com", full_name="Chat One", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT)
        cls.other_user = User(id=cls.other_user_id, email="chat-two@example.com", full_name="Chat Two", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT)
        database.add_all([cls.user, cls.other_user])
        database.add_all([
            StudentProfile(user_id=cls.user.id, exam_target="NDA"),
            StudentProfile(user_id=cls.other_user.id, exam_target="NDA"),
        ])
        database.commit()
        database.close()
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}
        cls.other_headers = {"Authorization": f"Bearer {create_access_token(str(cls.other_user_id), 'student')}"}

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        chat_route.SessionLocal = cls.session_factory
        cls.engine.dispose()

    def test_chat_lifecycle_and_message_history(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Probability help"})
        self.assertEqual(created.status_code, 201)
        session_id = created.json()["id"]

        message = self.client.post(
            f"/api/chats/{session_id}/messages",
            headers=self.headers,
            json={"content": "I need help with probability."},
        )
        self.assertEqual(message.status_code, 201)
        self.assertEqual(message.json()["role"], "user")

        detail = self.client.get(f"/api/chats/{session_id}", headers=self.headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["messages"][0]["content"], "I need help with probability.")

        renamed = self.client.patch(f"/api/chats/{session_id}", headers=self.headers, json={"title": "Probability"})
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["title"], "Probability")
        self.assertEqual(self.client.get("/api/chats", headers=self.headers).json()[0]["title"], "Probability")

        self.assertEqual(self.client.delete(f"/api/chats/{session_id}", headers=self.headers).status_code, 204)
        self.assertEqual(self.client.get(f"/api/chats/{session_id}", headers=self.headers).status_code, 404)

    def test_chat_is_private_to_owner(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Private"})
        session_id = created.json()["id"]
        self.assertEqual(self.client.get(f"/api/chats/{session_id}", headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.post(f"/api/chats/{session_id}/messages", headers=self.other_headers, json={"content": "No access"}).status_code, 404)

    def test_chat_requires_authentication(self) -> None:
        self.assertEqual(self.client.get("/api/chats").status_code, 401)

    def test_ai_completion_fails_explicitly_when_provider_is_disabled(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "AI disabled"})
        session_id = created.json()["id"]
        with patch("app.api.routes.chat.get_ai_provider", return_value=DisabledAIProvider()):
            response = self.client.post(
                f"/api/chats/{session_id}/messages/complete",
                headers=self.headers,
                json={"content": "Explain probability."},
            )
        self.assertEqual(response.status_code, 503)

    def test_oral_explanation_requests_speech_friendly_response_without_changing_saved_question(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Oral explanation"})
        session_id = created.json()["id"]
        with patch("app.api.routes.chat.get_ai_provider") as provider_factory:
            provider_factory.return_value.generate.return_value = "Let us solve it together."
            response = self.client.post(
                f"/api/chats/{session_id}/messages/complete",
                headers=self.headers,
                json={"content": "Explain probability.", "oral_explanation": True},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user_message"]["content"], "Explain probability.")
        provider_messages = provider_factory.return_value.generate.call_args.args[0]
        oral_prompt = next(message["content"] for message in provider_messages if message["role"] == "system" and "oral explanation" in message["content"])
        self.assertIn("short sentences", oral_prompt)
        self.assertIn("Avoid Markdown headings", oral_prompt)
        self.assertIn("most recent explicit language request", oral_prompt)

    def test_image_attachment_is_saved_returned_downloadable_and_sent_to_ai(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Image question"})
        session_id = created.json()["id"]
        image_buffer = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(image_buffer, format="PNG")
        encoded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")
        with patch("app.api.routes.chat.get_ai_provider") as provider_factory:
            provider_factory.return_value.generate.return_value = "This image shows a diagram."
            response = self.client.post(
                f"/api/chats/{session_id}/messages/complete",
                headers=self.headers,
                json={
                    "content": "Explain this diagram.",
                    "attachments": [{
                        "file_name": "diagram.png",
                        "media_type": "image/png",
                        "data_base64": encoded_image,
                    }],
                },
            )

        self.assertEqual(response.status_code, 201)
        message = response.json()["user_message"]
        self.assertEqual(message["attachments"][0]["file_name"], "diagram.png")
        self.assertNotIn("data_base64", message["attachments"][0])
        provider_attachments = provider_factory.return_value.generate.call_args.args[0][-1]["attachments"]
        self.assertEqual(provider_attachments[0]["data_base64"], encoded_image)

        downloaded = self.client.get(
            f"/api/chats/{session_id}/messages/{message['id']}/attachments/{message['attachments'][0]['id']}",
            headers=self.headers,
        )
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, image_buffer.getvalue())
        self.assertEqual(
            self.client.get(
                f"/api/chats/{session_id}/messages/{message['id']}/attachments/{message['attachments'][0]['id']}",
                headers=self.other_headers,
            ).status_code,
            404,
        )

    def test_attachment_format_is_checked_against_image_content(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Invalid image"})
        session_id = created.json()["id"]
        response = self.client.post(
            f"/api/chats/{session_id}/messages/complete",
            headers=self.headers,
            json={
                "content": "Explain this file.",
                "attachments": [{
                    "file_name": "fake.png",
                    "media_type": "image/png",
                    "data_base64": base64.b64encode(b"not an image").decode("ascii"),
                }],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_pdf_attachment_is_passed_to_multimodal_provider(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "PDF question"})
        session_id = created.json()["id"]
        pdf_data = b"%PDF-1.4\nminimal test document"
        encoded_pdf = base64.b64encode(pdf_data).decode("ascii")
        with patch("app.api.routes.chat.get_ai_provider") as provider_factory:
            provider_factory.return_value.generate.return_value = "The document explains algebra."
            response = self.client.post(
                f"/api/chats/{session_id}/messages/complete",
                headers=self.headers,
                json={
                    "content": "Summarize this document.",
                    "attachments": [{
                        "file_name": "lesson.pdf",
                        "media_type": "application/pdf",
                        "data_base64": encoded_pdf,
                    }],
                },
            )

        self.assertEqual(response.status_code, 201)
        provider_attachments = provider_factory.return_value.generate.call_args.args[0][-1]["attachments"]
        self.assertEqual(provider_attachments[0]["media_type"], "application/pdf")

    def test_unrelated_chat_is_redirected_without_calling_ai_provider(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Focus"})
        session_id = created.json()["id"]
        with patch("app.api.routes.chat.get_ai_provider") as provider_factory:
            response = self.client.post(
                f"/api/chats/{session_id}/messages/complete",
                headers=self.headers,
                json={"content": "Tell me a cricket joke"},
            )
        self.assertEqual(response.status_code, 201)
        self.assertIn("**Do not lose your focus.**", response.json()["assistant_message"]["content"])
        provider_factory.assert_not_called()

    def test_ai_completion_returns_quota_error_without_paid_fallback(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Free quota"})
        session_id = created.json()["id"]
        with patch("app.api.routes.chat.get_ai_provider") as provider_factory:
            provider_factory.return_value.generate.side_effect = AIProviderQuotaExceeded("Free-tier quota reached")
            response = self.client.post(
                f"/api/chats/{session_id}/messages/complete",
                headers=self.headers,
                json={"content": "Explain probability."},
            )
        self.assertEqual(response.status_code, 429)
        self.assertIn("Free-tier quota reached", response.json()["detail"])

    def test_websocket_message_typing_and_ping_events(self) -> None:
        created = self.client.post("/api/chats", headers=self.headers, json={"title": "Realtime"})
        session_id = created.json()["id"]
        with self.client.websocket_connect(f"/api/chats/{session_id}/ws?token={create_access_token(str(self.user_id), 'student')}") as websocket:
            self.assertEqual(websocket.receive_json()["type"], "connected")
            websocket.send_json({"type": "typing", "is_typing": True})
            self.assertEqual(websocket.receive_json(), {"type": "typing", "is_typing": True})
            websocket.send_json({"type": "message", "content": "Realtime question"})
            event = websocket.receive_json()
            self.assertEqual(event["type"], "message")
            self.assertEqual(event["message"]["content"], "Realtime question")
            websocket.send_json({"type": "ping"})
            self.assertEqual(websocket.receive_json()["type"], "pong")


if __name__ == "__main__":
    unittest.main()
