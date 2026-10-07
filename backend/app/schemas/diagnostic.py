"""API contracts for deterministic Phase 8 diagnostics."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, QuestionType


class DiagnosticOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    display_order: int


class DiagnosticQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    concept_id: UUID | None
    prompt: str
    explanation: str | None
    difficulty: Difficulty
    question_type: QuestionType
    options: list[DiagnosticOptionResponse] = Field(default_factory=list)


class DiagnosticStartResponse(BaseModel):
    target_concept_id: UUID
    question_count: int
    questions: list[DiagnosticQuestionResponse]


class DiagnosticAnswerRequest(BaseModel):
    selected_option_id: UUID | None = None
    answer_text: str | None = Field(default=None, max_length=2000)
    response_time_seconds: int | None = Field(default=None, ge=0, le=86400)
    hints_used: int = Field(default=0, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)


class DiagnosticAnswerResponse(BaseModel):
    question_id: UUID
    concept_id: UUID | None
    is_correct: bool
    mastery_score: float | None
    explanation: str | None
    next_step: str
