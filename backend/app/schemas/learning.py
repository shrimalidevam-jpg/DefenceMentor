"""API contracts for personalized Phase 9 learning flows."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Difficulty, QuestionType


class LearningSessionCreateRequest(BaseModel):
    target_concept_id: UUID
    objective: str | None = Field(default=None, max_length=500)


class LearningPathItem(BaseModel):
    concept_id: UUID
    name: str
    description: str | None
    is_target: bool
    mastery_score: float
    status: str
    completion_percent: float


class LearningSessionResponse(BaseModel):
    id: UUID
    target_concept_id: UUID
    current_concept_id: UUID | None
    status: str
    objective: str | None
    path: list[LearningPathItem]


class LessonResponse(BaseModel):
    concept_id: UUID
    title: str
    definition: str
    example: str
    practice_guidance: str
    mastery_score: float


class PracticeOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    display_order: int


class PracticeQuestionResponse(BaseModel):
    id: UUID
    concept_id: UUID | None
    prompt: str
    difficulty: Difficulty
    question_type: QuestionType
    options: list[PracticeOptionResponse] = Field(default_factory=list)


class LearningAnswerRequest(BaseModel):
    selected_option_id: UUID | None = None
    answer_text: str | None = Field(default=None, max_length=2000)
    response_time_seconds: int | None = Field(default=None, ge=0, le=86400)
    hints_used: int = Field(default=0, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    activity_type: str = Field(default="practice", pattern="^(practice|understanding_check)$")


class LearningAnswerResponse(BaseModel):
    question_id: UUID
    concept_id: UUID | None
    activity_type: str
    is_correct: bool
    mastery_score: float | None
    completion_percent: float
    concept_status: str
    next_concept_id: UUID | None
    explanation: str | None