"""Tests for secure application defaults and HTTP response headers."""

import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import app


class SecurityConfigurationTests(unittest.TestCase):
    def test_development_defaults_bind_to_loopback_and_allow_https_frontend(self) -> None:
        config = Settings(_env_file=None)

        self.assertEqual(config.HOST, "127.0.0.1")
        self.assertIn("https://localhost:5173", config.cors_origins_list)

    def test_production_rejects_debug_mode(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, APP_ENV="production", DEBUG=True)

    def test_production_rejects_default_secret(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, APP_ENV="production", DEBUG=False)

    def test_production_rejects_wildcard_cors(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                APP_ENV="production",
                DEBUG=False,
                SECRET_KEY="unique-test-secret-key-at-least-32-chars",
                CORS_ORIGINS="*",
            )

    def test_production_accepts_explicit_secure_settings(self) -> None:
        config = Settings(
            _env_file=None,
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="unique-test-secret-key-at-least-32-chars",
        )

        self.assertFalse(config.DEBUG)

    def test_api_sets_security_headers(self) -> None:
        with TestClient(app, base_url="https://testserver") as client:
            response = client.get("/api/health")

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(response.headers["Permissions-Policy"], "camera=(), microphone=(self), geolocation=()")
        self.assertEqual(response.headers["Strict-Transport-Security"], "max-age=31536000")


if __name__ == "__main__":
    unittest.main()
