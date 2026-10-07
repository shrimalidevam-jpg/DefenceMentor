"""Daily revision test API contracts."""

from uuid import UUID
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DailyReviewOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    display_order: int


class DailyReviewQuestionResponse(BaseModel):
    id: UUID
    prompt: str
    difficulty: str
    question_number: int
    total_questions: int
    options: list[DailyReviewOptionResponse] = Field(default_factory=list)


class DailyReviewResponse(BaseModel):
    id: UUID
    plan_date: date
    attempt_no: int
    status: str
    answered_count: int
    question_count: int
    correct_answers: int
    score: float | None
    score_marks: int
    max_marks: int
    question: DailyReviewQuestionResponse | None


class DailyReviewAnswerRequest(BaseModel):
    question_id: UUID
    selected_option_id: UUID


class DailyReviewAnswerResponse(BaseModel):
    is_correct: bool | None
    explanation: str | None
    answered_count: int
    correct_answers: int
    completed: bool
    score: float | None
    score_marks: int
    max_marks: int
    next_question: DailyReviewQuestionResponse | None
