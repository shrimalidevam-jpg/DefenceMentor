"""Authentication and guardian-consent API tests."""

import base64
from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.enums import UserRole
from app.models.users import User


def registration_payload(email: str) -> dict[str, object]:
    image = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(image, format="PNG")
    photo = "data:image/png;base64," + base64.b64encode(image.getvalue()).decode("ascii")
    return {
        "full_name": "Aditi Sharma",
        "email": email,
        "password": "SecurePass9",
        "exam_target": "NDA II 2027",
        "academic_stream": "Science",
        "science_group": "A",
        "parent_phone": "+919876543210",
        "student_photo_data": photo,
        "parent_photo_data": photo,
        "guardian_report_consent": True,
    }


class AuthenticationApiTests(unittest.TestCase):
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

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_registration_login_profile_and_admin_protection(self) -> None:
        registration = self.client.post(
            "/api/auth/register", json=registration_payload("aditi@example.com")
        )
        self.assertEqual(registration.status_code, 201)
        self.assertEqual(registration.json()["role"], "student")

        login = self.client.post(
            "/api/auth/login",
            json={"email": "aditi@example.com", "password": "SecurePass9"},
        )
        self.assertEqual(login.status_code, 200)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        profile = self.client.get("/api/auth/me/profile", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["parent_phone"], "+919876543210")
        self.assertTrue(profile.json()["guardian_report_consent_at"])
        self.assertEqual(
            self.client.patch(
                "/api/auth/me/profile",
                headers=headers,
                json={"current_level": "beginner"},
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/auth/admin/me", headers=headers).status_code, 403)

        database = self.session_factory()
        user = database.query(User).filter_by(email="aditi@example.com").one()
        user.role = UserRole.ADMIN
        database.commit()
        database.close()
        self.assertEqual(self.client.get("/api/auth/admin/me", headers=headers).status_code, 200)

    def test_guardian_can_withdraw_report_consent(self) -> None:
        self.client.post("/api/auth/register", json=registration_payload("withdraw@example.com"))
        login = self.client.post(
            "/api/auth/login",
            json={"email": "withdraw@example.com", "password": "SecurePass9"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = self.client.patch(
            "/api/auth/me/profile",
            headers=headers,
            json={"guardian_report_consent": False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["guardian_report_consent_at"])

    def test_registration_requires_guardian_consent_and_valid_whatsapp_phone(self) -> None:
        payload = registration_payload("no-consent@example.com")
        payload["guardian_report_consent"] = False
        self.assertEqual(self.client.post("/api/auth/register", json=payload).status_code, 422)

        payload = registration_payload("bad-phone@example.com")
        payload["parent_phone"] = "9876543210"
        self.assertEqual(self.client.post("/api/auth/register", json=payload).status_code, 422)

    def test_google_login_requires_a_registered_account(self) -> None:
        claims = {"email": "google@example.com", "name": "Google Learner", "email_verified": True}
        with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client"), patch(
            "app.api.routes.auth.id_token.verify_oauth2_token", return_value=claims
        ):
            unknown_user = self.client.post("/api/auth/google", json={"credential": "g" * 20})
            self.assertEqual(unknown_user.status_code, 409)

            self.client.post("/api/auth/register", json=registration_payload("google@example.com"))
            login = self.client.post("/api/auth/google", json={"credential": "g" * 20})
            self.assertEqual(login.status_code, 200)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            self.assertEqual(self.client.get("/api/auth/me", headers=headers).json()["email"], "google@example.com")

            reused_login = self.client.post("/api/auth/google", json={"credential": "g" * 20})
            self.assertEqual(reused_login.status_code, 200)


if __name__ == "__main__":
    unittest.main()
