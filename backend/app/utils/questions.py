"""Shared question and answer validation for API endpoints."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.questions import QuestionOption


def get_question_option(database: Session, question_id: UUID, option_id: UUID) -> QuestionOption:
    option = database.scalar(
        select(QuestionOption).where(
            QuestionOption.id == option_id,
            QuestionOption.question_id == question_id,
        )
    )
    if option is None:
        raise HTTPException(status_code=422, detail="Selected option does not belong to this question")
    return option
