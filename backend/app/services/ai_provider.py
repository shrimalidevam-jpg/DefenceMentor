"""Provider abstraction for optional Phase 12 tutor responses."""

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Mapping, Protocol, Sequence
from urllib.parse import urlparse

import httpx

from app.core.config import settings


class AIProviderError(RuntimeError):
    """Raised when an enabled provider cannot produce a response."""


class AIProviderUnavailable(AIProviderError):
    """Raised when no provider is configured for the environment."""


class AIProviderQuotaExceeded(AIProviderError):
    """Raised when a provider's free quota or rate limit has been reached."""


class AIProvider(Protocol):
    def generate(self, messages: Sequence[Mapping[str, object]]) -> str:
        """Generate a tutor response from structured conversation messages."""


@dataclass(frozen=True)
class GeminiFreeProvider:
    """Gemini free-tier-only provider with no retry or paid-provider fallback."""

    api_key: str
    timeout_seconds: float

    def generate(self, messages: Sequence[Mapping[str, object]]) -> str:
        system_instruction = "\n\n".join(
            str(item["content"]) for item in messages if item.get("role") == "system"
        )
        generation_config: dict[str, object] = {"temperature": 0.2}
        if "return only json" in system_instruction.casefold():
            generation_config["responseMimeType"] = "application/json"
        try:
            contents: list[dict[str, object]] = []
            for item in messages:
                if item.get("role") == "system":
                    continue
                parts: list[dict[str, object]] = [{"text": str(item["content"])}]
                attachments = item.get("attachments", [])
                if isinstance(attachments, list):
                    for attachment in attachments:
                        if not isinstance(attachment, dict):
                            continue
                        parts.append({
                            "inline_data": {
                                "mime_type": attachment["media_type"],
                                "data": attachment["data_base64"],
                            }
                        })
                contents.append({
                    "role": "model" if item.get("role") == "assistant" else "user",
                    "parts": parts,
                })

            response = httpx.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "contents": contents,
                    "systemInstruction": {
                        "parts": [{"text": system_instruction}]
                    },
                    "generationConfig": generation_config,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            parts = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            content = "".join(part.get("text", "") for part in parts)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                raise AIProviderQuotaExceeded("Gemini free-tier quota/rate limit reached. No paid fallback was attempted; retry later.") from error
            raise AIProviderError("The configured free-tier AI provider could not complete the request") from error
        except (httpx.HTTPError, ValueError, IndexError, KeyError, TypeError) as error:
            raise AIProviderError("The configured free-tier AI provider could not complete the request") from error
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("The configured free-tier AI provider returned an empty response")
        return content.strip()


@dataclass(frozen=True)
class OllamaProvider:
    """Local Ollama provider; it requires no account, key or paid credits."""

    base_url: str
    model: str
    timeout_seconds: float

    def generate(self, messages: Sequence[Mapping[str, object]]) -> str:
        system_instruction = "\n\n".join(
            str(item["content"]) for item in messages if item.get("role") == "system"
        )
        ollama_messages: list[dict[str, object]] = []
        for item in messages:
            if item.get("role") == "system":
                continue
            content = str(item["content"])
            images: list[str] = []
            attachments = item.get("attachments", [])
            if isinstance(attachments, list):
                for attachment in attachments:
                    if not isinstance(attachment, dict):
                        continue
                    if str(attachment.get("media_type", "")).startswith("image/"):
                        images.append(str(attachment["data_base64"]))
                    else:
                        raise AIProviderError(
                            "PDF analysis is not supported by the local Ollama provider. Configure Gemini Free to analyze PDF attachments."
                        )
            ollama_message: dict[str, object] = {
                "role": "assistant" if item.get("role") == "assistant" else "user",
                "content": content,
            }
            if images:
                ollama_message["images"] = images
            ollama_messages.append(ollama_message)
        request_body: dict[str, object] = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        if "return only json" in system_instruction.casefold():
            request_body["format"] = "json"
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/api/chat",
                json=request_body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            content = response.json().get("message", {}).get("content")
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise AIProviderError("The local Ollama provider is not running or could not complete the request") from error
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("The local Ollama provider returned an empty response")
        return content.strip()


class DisabledAIProvider:
    def generate(self, messages: Sequence[Mapping[str, object]]) -> str:
        raise AIProviderUnavailable("AI provider is not configured")


def get_ai_provider() -> AIProvider:
    provider = settings.AI_PROVIDER.casefold()
    if provider == "gemini-free" and settings.GEMINI_FREE_API_KEY:
        return GeminiFreeProvider(settings.GEMINI_FREE_API_KEY, settings.AI_TIMEOUT_SECONDS)
    if provider == "ollama":
        parsed_url = urlparse(settings.AI_BASE_URL)
        hostname = parsed_url.hostname
        try:
            is_loopback = hostname == "localhost" or (hostname is not None and ip_address(hostname).is_loopback)
        except ValueError:
            is_loopback = False
        if parsed_url.scheme == "http" and is_loopback:
            return OllamaProvider(settings.AI_BASE_URL, settings.AI_MODEL, settings.AI_TIMEOUT_SECONDS)
    return DisabledAIProvider()