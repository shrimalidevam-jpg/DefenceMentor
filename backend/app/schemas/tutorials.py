"""API contracts for verified tutorial resources."""

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class TutorialResourceCreate(BaseModel):
    board: str = Field(min_length=2, max_length=40)
    grade_level: int = Field(ge=5, le=12)
    subject: str = Field(min_length=2, max_length=120)
    topic: str = Field(min_length=2, max_length=180)
    title: str = Field(min_length=3, max_length=255)
    url: AnyHttpUrl
    provider: str = Field(min_length=2, max_length=120)
    resource_type: str = Field(default="video", min_length=2, max_length=40)
    language: str = Field(default="English", min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=2000)


class TutorialResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    board: str
    grade_level: int
    subject: str
    topic: str
    title: str
    url: str
    provider: str
    resource_type: str
    language: str
    description: str | None
    is_verified: bool
    is_published: bool
    verified_at: datetime | None


class TutorialPublishRequest(BaseModel):
    is_verified: bool
    is_published: bool
