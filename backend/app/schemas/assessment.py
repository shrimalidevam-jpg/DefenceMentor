"""API contracts for the Phase 11 adaptive examination."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, QuestionType


class AssessmentStartRequest(BaseModel):
    exam_id: UUID
    schedule_type: Literal["weekly", "monthly"] = "weekly"


class AssessmentOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    display_order: int


class AssessmentQuestionResponse(BaseModel):
    id: UUID
    prompt: str
    difficulty: Difficulty
    question_type: QuestionType
    round_name: str
    question_number: int
    total_questions: int
    is_ai_generated: bool = False
    selected_option_id: UUID | None = None
    options: list[AssessmentOptionResponse] = Field(default_factory=list)


class AssessmentAttemptResponse(BaseModel):
    id: UUID
    status: str
    current_round: str
    answered_count: int
    schedule_type: str = "weekly"
    section_time_limit_seconds: int
    section_elapsed_seconds: int
    section_completed: bool
    same_day_deadline: datetime | None = None
    total_exam_questions: int
    score: float | None
    question: AssessmentQuestionResponse | None


class AssessmentNavigateRequest(BaseModel):
    current_question_id: UUID
    selected_option_id: UUID | None = None
    target_question_number: int = Field(ge=1)


class AssessmentSubmitRequest(BaseModel):
    current_question_id: UUID
    selected_option_id: UUID | None = None


class AssessmentReportResponse(BaseModel):
    attempt_id: UUID
    status: str
    score: float
    total_questions: int
    correct_answers: int
    accuracy: float
    round_performance: dict[str, float]
    difficulty_performance: dict[str, dict[str, float]] = Field(default_factory=dict)
    subject_performance: dict[str, dict[str, float]] = Field(default_factory=dict)
    topic_performance: dict[str, dict[str, float]] = Field(default_factory=dict)
    average_response_time_seconds: float = 0
    net_marks: float = 0
    maximum_marks: float = 0
    recommendations: list[str] = Field(default_factory=list)


class AssessmentHistoryItem(BaseModel):
    id: UUID
    schedule_type: str
    status: str
    score: float | None
    answered_count: int
    started_at: datetime
    completed_at: datetime | None


class AssessmentHistoryResponse(BaseModel):
    exam_id: UUID
    total_attempts: int
    completed_attempts: int
    average_score: float | None
    previous_average_score: float | None
    improvement_points: float | None
    weekly_due: bool
    monthly_due: bool
    history: list[AssessmentHistoryItem] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)