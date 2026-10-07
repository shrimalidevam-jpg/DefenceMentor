"""Phase 12 provider boundary and unavailable-provider behavior tests."""

import unittest
from unittest.mock import Mock, patch

import httpx

from app.services.ai_provider import AIProviderError, AIProviderQuotaExceeded, AIProviderUnavailable, DisabledAIProvider, GeminiFreeProvider, OllamaProvider, get_ai_provider


class AIProviderTests(unittest.TestCase):
    def test_disabled_provider_never_returns_fake_content(self) -> None:
        with self.assertRaises(AIProviderUnavailable):
            DisabledAIProvider().generate([{"role": "user", "content": "Explain probability"}])

    def test_provider_factory_uses_disabled_by_default(self) -> None:
        with patch("app.services.ai_provider.settings.AI_PROVIDER", "disabled"):
            self.assertIsInstance(get_ai_provider(), DisabledAIProvider)

    def test_provider_factory_supports_local_ollama_without_a_key(self) -> None:
        with patch("app.services.ai_provider.settings.AI_PROVIDER", "ollama"):
            self.assertIsInstance(get_ai_provider(), OllamaProvider)

    def test_provider_factory_never_enables_cloud_ai(self) -> None:
        for provider in ("gemini", "openai", "openai-compatible"):
            with self.subTest(provider=provider), patch("app.services.ai_provider.settings.AI_PROVIDER", provider):
                self.assertIsInstance(get_ai_provider(), DisabledAIProvider)

    def test_provider_factory_uses_gemini_free_only_with_dedicated_key(self) -> None:
        with patch("app.services.ai_provider.settings.AI_PROVIDER", "gemini-free"), patch(
            "app.services.ai_provider.settings.GEMINI_FREE_API_KEY", "test-key"
        ):
            self.assertIsInstance(get_ai_provider(), GeminiFreeProvider)

    def test_free_quota_error_is_not_retried_or_fallen_back(self) -> None:
        request = httpx.Request("POST", "https://generativelanguage.googleapis.com/test")
        response = httpx.Response(429, request=request)
        error = httpx.HTTPStatusError("quota", request=request, response=response)
        with patch("app.services.ai_provider.httpx.post", side_effect=error) as post:
            with self.assertRaises(AIProviderQuotaExceeded):
                GeminiFreeProvider("test-key", 1).generate([{"role": "user", "content": "Explain probability"}])
        post.assert_called_once()

    def test_gemini_requests_json_mode_for_structured_generation_only(self) -> None:
        response = Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"questions": []}'}]}}]
        }
        response.raise_for_status.return_value = None
        structured_messages = [
            {"role": "system", "content": "Return only JSON for generated questions."},
            {"role": "user", "content": "Generate questions."},
        ]
        with patch("app.services.ai_provider.httpx.post", return_value=response) as post:
            GeminiFreeProvider("test-key", 1).generate(structured_messages)
        self.assertEqual(
            post.call_args.kwargs["json"]["generationConfig"]["responseMimeType"],
            "application/json",
        )

        with patch("app.services.ai_provider.httpx.post", return_value=response) as post:
            GeminiFreeProvider("test-key", 1).generate([{"role": "user", "content": "Explain probability"}])
        self.assertNotIn("responseMimeType", post.call_args.kwargs["json"]["generationConfig"])

    def test_gemini_sends_image_and_pdf_as_inline_attachments(self) -> None:
        response = Mock()
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "I can see the attachment."}]}}]}
        response.raise_for_status.return_value = None
        attachment_messages = [{
            "role": "user",
            "content": "Please explain this.",
            "attachments": [
                {"file_name": "diagram.png", "media_type": "image/png", "data_base64": "aW1hZ2U="},
                {"file_name": "notes.pdf", "media_type": "application/pdf", "data_base64": "cGRm"},
            ],
        }]

        with patch("app.services.ai_provider.httpx.post", return_value=response) as post:
            GeminiFreeProvider("test-key", 1).generate(attachment_messages)

        parts = post.call_args.kwargs["json"]["contents"][0]["parts"]
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "image/png")
        self.assertEqual(parts[2]["inline_data"]["mime_type"], "application/pdf")

    def test_ollama_requests_json_mode_for_structured_generation_only(self) -> None:
        response = Mock()
        response.json.return_value = {"message": {"content": '{"questions": []}'}}
        response.raise_for_status.return_value = None
        structured_messages = [
            {"role": "system", "content": "Return only JSON for generated questions."},
            {"role": "user", "content": "Generate questions."},
        ]
        with patch("app.services.ai_provider.httpx.post", return_value=response) as post:
            OllamaProvider("http://127.0.0.1:11434", "test-model", 1).generate(structured_messages)
        self.assertEqual(post.call_args.kwargs["json"]["format"], "json")

        with patch("app.services.ai_provider.httpx.post", return_value=response) as post:
            OllamaProvider("http://127.0.0.1:11434", "test-model", 1).generate(
                [{"role": "user", "content": "Explain probability"}]
            )
        self.assertNotIn("format", post.call_args.kwargs["json"])

    def test_ollama_sends_images_and_reports_unsupported_pdf(self) -> None:
        response = Mock()
        response.json.return_value = {"message": {"content": "Image understood."}}
        response.raise_for_status.return_value = None
        image_messages = [{
            "role": "user",
            "content": "Describe it.",
            "attachments": [{"file_name": "diagram.png", "media_type": "image/png", "data_base64": "aW1hZ2U="}],
        }]
        with patch("app.services.ai_provider.httpx.post", return_value=response) as post:
            OllamaProvider("http://127.0.0.1:11434", "test-model", 1).generate(image_messages)
        self.assertEqual(post.call_args.kwargs["json"]["messages"][0]["images"], ["aW1hZ2U="])

        pdf_messages = [{
            "role": "user",
            "content": "Explain it.",
            "attachments": [{"file_name": "notes.pdf", "media_type": "application/pdf", "data_base64": "cGRm"}],
        }]
        with self.assertRaisesRegex(AIProviderError, "PDF analysis is not supported"):
            OllamaProvider("http://127.0.0.1:11434", "test-model", 1).generate(pdf_messages)

    def test_provider_factory_rejects_remote_ollama_urls(self) -> None:
        with patch("app.services.ai_provider.settings.AI_PROVIDER", "ollama"), patch(
            "app.services.ai_provider.settings.AI_BASE_URL", "https://api.example.com"
        ):
            self.assertIsInstance(get_ai_provider(), DisabledAIProvider)


if __name__ == "__main__":
    unittest.main()