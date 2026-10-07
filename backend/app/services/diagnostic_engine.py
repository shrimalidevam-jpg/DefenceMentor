"""Transparent rule-based diagnostic evaluation for Phase 8."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.questions import Question, QuestionAnswer, QuestionAttempt
from app.services.mastery_engine import update_mastery


def evaluate_answer(
    database: Session,
    user_id: UUID,
    question: Question,
    selected_option_id: UUID | None,
    answer_text: str | None,
    response_time_seconds: int | None,
    hints_used: int,
    confidence: float | None = None,
) -> tuple[bool, float | None]:
    answer = database.scalar(select(QuestionAnswer).where(QuestionAnswer.question_id == question.id))
    if answer is None:
        raise ValueError("This question does not have a configured answer")

    is_correct = False
    if selected_option_id is not None and answer.correct_option_id is not None:
        is_correct = selected_option_id == answer.correct_option_id
    elif answer_text is not None and answer.correct_text is not None:
        is_correct = answer_text.strip().casefold() == answer.correct_text.strip().casefold()

    attempt = QuestionAttempt(
        user_id=user_id,
        question_id=question.id,
        selected_option_id=selected_option_id,
        answer_text=answer_text.strip() if answer_text else None,
        is_correct=is_correct,
        response_time_seconds=response_time_seconds,
        hints_used=hints_used,
        confidence=confidence,
    )
    database.add(attempt)

    mastery_score: float | None = None
    if question.concept_id is not None:
        database.flush()
        mastery_score = update_mastery(database, user_id, question.concept_id)

    database.commit()
    return is_correct, mastery_score
