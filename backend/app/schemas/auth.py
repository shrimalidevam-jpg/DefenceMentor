"""Validated API contracts for registration, login and profiles."""

from datetime import date
import base64
import binascii
import re
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    exam_target: str = Field(default="NDA", min_length=2, max_length=100)
    current_level: str | None = Field(default=None, max_length=50)
    academic_stream: Literal["Science", "Commerce", "Arts"]
    science_group: Literal["A", "B"] | None = None
    student_phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    parent_phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    student_photo_data: str
    parent_photo_data: str
    guardian_report_consent: bool

    @field_validator("student_photo_data", "parent_photo_data")
    @classmethod
    def validate_photo_data(cls, value: str) -> str:
        match = re.fullmatch(r"data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)", value)
        if match is None:
            raise ValueError("Upload a JPEG, PNG, or WebP image")
        try:
            image = base64.b64decode(match.group(2), validate=True)
        except binascii.Error as error:
            raise ValueError("The uploaded image data is invalid") from error
        if not image or len(image) > 2 * 1024 * 1024:
            raise ValueError("Each photo must be smaller than 2 MB")
        signatures = {
            "image/jpeg": image.startswith(b"\xff\xd8\xff"),
            "image/png": image.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": len(image) >= 12 and image[:4] == b"RIFF" and image[8:12] == b"WEBP",
        }
        if not signatures[match.group(1)]:
            raise ValueError("The uploaded file does not match its image type")
        return value

    @model_validator(mode="after")
    def validate_science_group(self) -> "RegisterRequest":
        if self.academic_stream == "Science" and self.science_group is None:
            raise ValueError("Choose Science Group A or B")
        if self.academic_stream != "Science" and self.science_group is not None:
            raise ValueError("Science group can only be selected for the Science stream")
        if not self.guardian_report_consent:
            raise ValueError("Parent or legal guardian consent is required")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=10000)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    exam_target: str
    current_level: str | None
    target_exam_date: date | None
    learning_preferences: str | None
    academic_stream: str | None
    science_group: str | None
    student_phone: str | None
    parent_phone: str | None
    guardian_report_consent_at: date | None


class ProfileUpdateRequest(BaseModel):
    exam_target: str | None = Field(default=None, min_length=2, max_length=100)
    current_level: str | None = Field(default=None, max_length=50)
    target_exam_date: date | None = None
    learning_preferences: str | None = Field(default=None, max_length=2000)
    academic_stream: Literal["Science", "Commerce", "Arts"] | None = None
    science_group: Literal["A", "B"] | None = None
    student_phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")
    guardian_report_consent: bool | None = None

    @model_validator(mode="after")
    def validate_science_group(self) -> "ProfileUpdateRequest":
        if self.academic_stream == "Science" and self.science_group is None:
            raise ValueError("Choose Science Group A or B")
        if self.academic_stream in {"Commerce", "Arts"} and self.science_group is not None:
            raise ValueError("Science group can only be selected for the Science stream")
        return self
