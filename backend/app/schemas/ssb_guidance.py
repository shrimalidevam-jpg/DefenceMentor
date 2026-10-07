"""API schemas for daily SSB guidance and coaching chat."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DailySSBGuidanceResponse(BaseModel):
    guidance_date: date
    title: str
    guidance: str
    action: str
    reflection_question: str


class SSBGuidanceMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class SSBGuidanceMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class SSBGuidanceChatResponse(BaseModel):
    messages: list[SSBGuidanceMessageResponse]
