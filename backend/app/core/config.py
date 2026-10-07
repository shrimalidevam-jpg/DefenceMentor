from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "NDA Chatbot API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    DATABASE_URL: str = "postgresql://nda_user:nda_password@localhost:5432/nda_chatbot"

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MASTERY_THRESHOLD: float = 80.0
    MASTERY_RECENCY_WEIGHT: float = 0.15
    ADAPTIVE_HIGH_THRESHOLD: float = 0.8
    ADAPTIVE_MEDIUM_THRESHOLD: float = 0.5
    ADAPTIVE_QUESTIONS_PER_ROUND: int = 5
    AI_PROVIDER: str = "disabled"
    AI_API_KEY: str | None = None
    GEMINI_FREE_API_KEY: str | None = None
    AI_BASE_URL: str = "http://127.0.0.1:11434"
    AI_MODEL: str = "llama3.2:3b"
    AI_TIMEOUT_SECONDS: float = 30.0
    GOOGLE_CLIENT_ID: str = ""
    APP_TIMEZONE: str = "Asia/Kolkata"
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_TEMPLATE_NAME: str = "nda_progress_report"
    WHATSAPP_TEMPLATE_LANGUAGE: str = "en"
    WHATSAPP_API_VERSION: str = "v22.0"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://localhost:5173,https://127.0.0.1:5173"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def coerce_debug_value(cls, value: object) -> bool:
        """Accept common deployment labels while retaining a strict boolean setting."""
        if isinstance(value, str) and value.lower() in {"release", "production"}:
            return False
        return value  # type: ignore[return-value]

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.APP_ENV.lower() not in {"production", "prod"}:
            return self
        if self.DEBUG:
            raise ValueError("DEBUG must be false when APP_ENV is production.")
        if len(self.SECRET_KEY) < 32 or self.SECRET_KEY in {
            "dev-secret-key-change-in-production",
            "change-this-to-a-long-random-secret-key-in-production",
        }:
            raise ValueError("Production requires a unique SECRET_KEY of at least 32 characters.")
        if "*" in self.cors_origins_list:
            raise ValueError("Production CORS_ORIGINS cannot contain a wildcard.")
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
