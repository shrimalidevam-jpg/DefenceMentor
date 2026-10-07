"""Authenticated diagnostic assessment endpoints for Phase 8."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.curriculum import Concept
from app.models.questions import Question, QuestionOption
from app.models.users import User
from app.schemas.diagnostic import (
    DiagnosticAnswerRequest,
    DiagnosticAnswerResponse,
    DiagnosticQuestionResponse,
    DiagnosticStartResponse,
)
from app.services.diagnostic_engine import evaluate_answer
from app.services.knowledge_graph import build_learning_path
from app.utils.questions import get_question_option


router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


def question_response(database: Session, question: Question) -> DiagnosticQuestionResponse:
    options = list(
        database.scalars(
            select(QuestionOption).where(QuestionOption.question_id == question.id).order_by(QuestionOption.display_order)
        )
    )
    return DiagnosticQuestionResponse.model_validate({**question.__dict__, "options": options}, from_attributes=True)


@router.post("/concepts/{concept_id}/start", response_model=DiagnosticStartResponse)
def start_diagnostic(
    concept_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DiagnosticStartResponse:
    if database.get(Concept, concept_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    try:
        learning_path = build_learning_path(database, concept_id)
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    concept_ids = [concept.id for concept in learning_path]
    questions = list(
        database.scalars(
            select(Question)
            .where(Question.concept_id.in_(concept_ids), Question.is_published.is_(True))
            .order_by(Question.display_order if hasattr(Question, "display_order") else Question.created_at)
        )
    )
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published diagnostic questions are available for this concept yet",
        )
    return DiagnosticStartResponse(
        target_concept_id=concept_id,
        question_count=len(questions),
        questions=[question_response(database, question) for question in questions],
    )


@router.post("/questions/{question_id}/answer", response_model=DiagnosticAnswerResponse)
def answer_diagnostic_question(
    question_id: UUID,
    payload: DiagnosticAnswerRequest,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DiagnosticAnswerResponse:
    question = database.scalar(select(Question).where(Question.id == question_id, Question.is_published.is_(True)))
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Published diagnostic question not found")
    if payload.selected_option_id is None and not payload.answer_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide an option or text answer")
    if payload.selected_option_id is not None:
        get_question_option(database, question_id, payload.selected_option_id)

    try:
        is_correct, mastery_score = evaluate_answer(
            database, current_user.id, question, payload.selected_option_id,
            payload.answer_text, payload.response_time_seconds, payload.hints_used,
            payload.confidence,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return DiagnosticAnswerResponse(
        question_id=question.id,
        concept_id=question.concept_id,
        is_correct=is_correct,
        mastery_score=mastery_score,
        explanation=question.explanation,
        next_step="Continue to the next diagnostic question" if is_correct else "Review the prerequisite concept before continuing",
    )
