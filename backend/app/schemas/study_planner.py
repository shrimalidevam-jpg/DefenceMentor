"""Study planner API response models."""

from datetime import date, datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudyPlanTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_date: date
    concept_id: UUID
    concept_name: str
    subject_name: str
    task_type: str
    estimated_minutes: int
    display_order: int
    mastery_score: float | None
    is_completed: bool
    completed_at: datetime | None


class StudyScheduleBlock(BaseModel):
    kind: str
    label: str
    start_time: str
    end_time: str
    duration_minutes: int
    task_id: UUID | None = None
    concept_name: str | None = None
    subject_name: str | None = None
    is_completed: bool = False


class StudyPlanResponse(BaseModel):
    plan_date: date
    exam_target: str
    target_exam_date: date | None
    days_to_exam: int | None
    total_minutes: int
    completed_count: int
    tasks: list[StudyPlanTaskResponse]
    schedule: list[StudyScheduleBlock]


class StudyPlannerPreferences(BaseModel):
    planner_setup_complete: bool
    daily_study_minutes: int
    study_start_time: str
    focus_session_minutes: int
    break_minutes: int
    study_subjects: list[Literal["MATH", "GAT"]]
    math_share_percent: int


class StudyPlannerPreferencesUpdate(BaseModel):
    daily_study_minutes: int = Field(ge=120, le=720)
    study_start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    focus_session_minutes: int = Field(ge=25, le=90)
    break_minutes: int = Field(ge=5, le=30)
    study_subjects: list[Literal["MATH", "GAT"]] = Field(min_length=1, max_length=2)
    math_share_percent: int = Field(ge=20, le=80)

    @field_validator("study_subjects")
    @classmethod
    def unique_study_subjects(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Choose each study subject only once")
        return value


class StudyPlanTaskUpdate(BaseModel):
    is_completed: bool


class StudyCalendarTask(BaseModel):
    id: UUID
    concept_name: str
    subject_name: str
    task_type: str
    estimated_minutes: int
    is_completed: bool
    completed_at: datetime | None


class StudyCalendarExam(BaseModel):
    id: UUID
    attempt_no: int
    status: str
    question_count: int
    answered_count: int
    correct_answers: int
    score_marks: int
    max_marks: int
    score_percent: float | None
    completed_at: datetime | None


class StudyCalendarDay(BaseModel):
    plan_date: date
    total_minutes: int
    completed_minutes: int
    completed_count: int
    tasks: list[StudyCalendarTask]
    exams: list[StudyCalendarExam]


class StudyCalendarResponse(BaseModel):
    month: str
    days: list[StudyCalendarDay]
