"""API contracts for Phase 10 mastery evidence."""

from uuid import UUID

from pydantic import BaseModel


class MasterySummaryResponse(BaseModel):
    concept_id: UUID
    mastery_score: float
    status: str
    attempt_count: int
    correct_count: int
    accuracy: float
    average_response_time_seconds: float | None
    hints_used: int