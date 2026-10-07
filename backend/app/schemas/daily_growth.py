"""Daily vocabulary and SSB preparation API contracts."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VocabularyQuestionResponse(BaseModel):
    id: str
    word: str
    options: dict[str, str]
    explanation: str | None = None
    example: str | None = None
    selected_option: str | None = None
    correct_option: str | None = None
    is_correct: bool | None = None


class DailyGrowthResponse(BaseModel):
    practice_date: date
    questions: list[VocabularyQuestionResponse]
    answered_count: int
    correct_count: int
    score_percent: float | None
    ssb_tip: str
    ssb_category: str
    ssb_title: str = "Daily SSB preparation tip"


class VocabularyAnswerRequest(BaseModel):
    word_id: str = Field(min_length=2, max_length=60)
    selected_option: str = Field(pattern="^[A-D]$")


class VocabularyAnswerResponse(BaseModel):
    word_id: str
    is_correct: bool
    correct_option: str
    meaning: str
    example: str
    answered_count: int
    correct_count: int
    score_percent: float
    answered_at: datetime
