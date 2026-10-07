"""API contracts for the Phase 4 curriculum hierarchy."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CurriculumBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    display_order: int = 0


class ExamResponse(CurriculumBaseResponse):
    code: str
    is_active: bool


class SubjectResponse(CurriculumBaseResponse):
    exam_id: UUID
    code: str


class ChapterResponse(CurriculumBaseResponse):
    subject_id: UUID


class TopicResponse(CurriculumBaseResponse):
    chapter_id: UUID


class ConceptResponse(CurriculumBaseResponse):
    topic_id: UUID


class PrerequisiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    concept_id: UUID
    prerequisite_concept_id: UUID
    is_required: bool


class LearningPathItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order: int
    concept: ConceptResponse
    is_target: bool


class CurriculumTreeResponse(BaseModel):
    """Small tree response for rendering the curriculum browser."""

    exam: ExamResponse
    subjects: list[SubjectResponse] = Field(default_factory=list)
