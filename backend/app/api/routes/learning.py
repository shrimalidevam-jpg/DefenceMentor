"""Personalized learning and practice endpoints for Phase 9."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.curriculum import Concept
from app.models.learning import LearningProgress, LearningSession
from app.models.questions import Question, QuestionOption
from app.models.users import User
from app.schemas.learning import (
    LearningAnswerRequest,
    LearningAnswerResponse,
    LearningPathItem,
    LearningSessionCreateRequest,
    LearningSessionResponse,
    LessonResponse,
    PracticeQuestionResponse,
)
from app.services.learning_engine import (
    answer_learning_question,
    current_concept_id,
    path_items,
    question_options,
    select_practice_question,
)
from app.utils.questions import get_question_option


router = APIRouter(prefix="/learning", tags=["Learning"])


def session_response(database: Session, user_id: UUID, session: LearningSession) -> LearningSessionResponse:
    path = path_items(database, user_id, session.target_concept_id)
    return LearningSessionResponse(
        id=session.id,
        target_concept_id=session.target_concept_id,
        current_concept_id=current_concept_id(path),
        status=session.status.value,
        objective=session.objective,
        path=[LearningPathItem.model_validate(item) for item in path],
    )


def owned_session(database: Session, user_id: UUID, session_id: UUID) -> LearningSession:
    session = database.scalar(
        select(LearningSession).where(LearningSession.id == session_id, LearningSession.user_id == user_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return session


@router.post("/sessions", response_model=LearningSessionResponse, status_code=status.HTTP_201_CREATED)
def create_learning_session(
    payload: LearningSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> LearningSessionResponse:
    if database.get(Concept, payload.target_concept_id) is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    try:
        path = path_items(database, current_user.id, payload.target_concept_id)
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    session = LearningSession(
        user_id=current_user.id,
        target_concept_id=payload.target_concept_id,
        current_concept_id=current_concept_id(path),
        objective=payload.objective or "Master the selected concept",
    )
    database.add(session)
    database.flush()
    for item in path:
        if item["status"] == "completed":
            database.add(
                LearningProgress(
                    session_id=session.id,
                    concept_id=item["concept_id"],
                    status="completed",
                    completion_percent=item["completion_percent"],
                )
            )
    database.commit()
    database.refresh(session)
    return session_response(database, current_user.id, session)


@router.get("/sessions/{session_id}", response_model=LearningSessionResponse)
def get_learning_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> LearningSessionResponse:
    return session_response(database, current_user.id, owned_session(database, current_user.id, session_id))


@router.get("/sessions/{session_id}/current/lesson", response_model=LessonResponse)
def get_current_lesson(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> LessonResponse:
    session = owned_session(database, current_user.id, session_id)
    if session.current_concept_id is None:
        raise HTTPException(status_code=404, detail="No current learning concept")
    concept = database.get(Concept, session.current_concept_id)
    if concept is None:
        raise HTTPException(status_code=404, detail="Current concept not found")
    score = next(
        item["mastery_score"]
        for item in path_items(database, current_user.id, session.target_concept_id)
        if item["concept_id"] == concept.id
    )
    return LessonResponse(
        concept_id=concept.id,
        title=concept.name,
        definition=concept.description or f"Build your understanding of {concept.name} before moving forward.",
        example=f"Start with a simple example of {concept.name}, then explain each step in your own words.",
        practice_guidance="Try the practice question without a hint first, then review the explanation.",
        mastery_score=score,
    )


@router.get("/sessions/{session_id}/current/practice", response_model=PracticeQuestionResponse)
def get_practice_question(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> PracticeQuestionResponse:
    session = owned_session(database, current_user.id, session_id)
    if session.current_concept_id is None:
        raise HTTPException(status_code=404, detail="No current learning concept")
    question = select_practice_question(database, current_user.id, session.current_concept_id)
    if question is None:
        raise HTTPException(status_code=404, detail="No published practice questions are available")
    return PracticeQuestionResponse.model_validate(
        {**question.__dict__, "options": question_options(database, question.id)},
        from_attributes=True,
    )


@router.post("/sessions/{session_id}/questions/{question_id}/answer", response_model=LearningAnswerResponse)
def answer_learning_question_endpoint(
    session_id: UUID,
    question_id: UUID,
    payload: LearningAnswerRequest,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> LearningAnswerResponse:
    session = owned_session(database, current_user.id, session_id)
    question = database.scalar(select(Question).where(Question.id == question_id, Question.is_published.is_(True)))
    if question is None or session.current_concept_id != question.concept_id:
        raise HTTPException(status_code=404, detail="Learning question is not available for this session")
    if payload.selected_option_id is None and not payload.answer_text:
        raise HTTPException(status_code=422, detail="Provide an option or text answer")
    if payload.selected_option_id is not None:
        get_question_option(database, question.id, payload.selected_option_id)
    try:
        is_correct, score, completion, concept_status, next_id = answer_learning_question(
            database,
            session,
            question,
            payload.selected_option_id,
            payload.answer_text,
            payload.response_time_seconds,
            payload.hints_used,
            payload.confidence,
            payload.activity_type,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return LearningAnswerResponse(
        question_id=question.id,
        concept_id=question.concept_id,
        activity_type=payload.activity_type,
        is_correct=is_correct,
        mastery_score=score,
        completion_percent=completion,
        concept_status=concept_status,
        next_concept_id=next_id,
        explanation=question.explanation,
    )
