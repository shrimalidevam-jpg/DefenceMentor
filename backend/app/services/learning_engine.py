"""Deterministic personalized learning orchestration for Phase 9."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.curriculum import Concept
from app.models.learning import LearningProgress, LearningSession, StudentMastery
from app.core.config import settings
from app.models.questions import Question, QuestionAttempt, QuestionOption
from app.services.diagnostic_engine import evaluate_answer
from app.services.knowledge_graph import build_learning_path


MASTERY_THRESHOLD = settings.MASTERY_THRESHOLD


def mastery_score(database: Session, user_id: UUID, concept_id: UUID) -> float:
    mastery = database.scalar(
        select(StudentMastery).where(
            StudentMastery.user_id == user_id,
            StudentMastery.concept_id == concept_id,
        )
    )
    return round(float(mastery.score), 2) if mastery is not None else 0.0


def path_items(database: Session, user_id: UUID, target_concept_id: UUID) -> list[dict]:
    concepts = build_learning_path(database, target_concept_id)
    items: list[dict] = []
    for concept in concepts:
        score = mastery_score(database, user_id, concept.id)
        items.append(
            {
                "concept_id": concept.id,
                "name": concept.name,
                "description": concept.description,
                "is_target": concept.id == target_concept_id,
                "mastery_score": score,
                "status": "completed" if score >= MASTERY_THRESHOLD else "not_started",
                "completion_percent": min(score, 100.0),
            }
        )
    return items


def current_concept_id(path: list[dict]) -> UUID | None:
    return next((item["concept_id"] for item in path if item["mastery_score"] < MASTERY_THRESHOLD), None)


def get_or_create_progress(database: Session, session_id: UUID, concept_id: UUID, score: float) -> LearningProgress:
    progress = database.scalar(
        select(LearningProgress).where(
            LearningProgress.session_id == session_id,
            LearningProgress.concept_id == concept_id,
        )
    )
    if progress is None:
        progress = LearningProgress(session_id=session_id, concept_id=concept_id)
        database.add(progress)
    progress.completion_percent = min(score, 100.0)
    progress.status = "completed" if score >= MASTERY_THRESHOLD else "in_progress"
    return progress


def question_options(database: Session, question_id: UUID) -> list[QuestionOption]:
    return list(
        database.scalars(
            select(QuestionOption).where(QuestionOption.question_id == question_id).order_by(QuestionOption.display_order)
        )
    )


def select_practice_question(database: Session, user_id: UUID, concept_id: UUID) -> Question | None:
    attempted_ids = select(QuestionAttempt.question_id).where(QuestionAttempt.user_id == user_id)
    question = database.scalar(
        select(Question)
        .where(
            Question.concept_id == concept_id,
            Question.is_published.is_(True),
            ~Question.id.in_(attempted_ids),
        )
        .order_by(Question.created_at)
    )
    if question is not None:
        return question
    return database.scalar(
        select(Question)
        .where(Question.concept_id == concept_id, Question.is_published.is_(True))
        .order_by(Question.created_at)
    )


def answer_learning_question(
    database: Session,
    session: LearningSession,
    question: Question,
    selected_option_id: UUID | None,
    answer_text: str | None,
    response_time_seconds: int | None,
    hints_used: int,
    confidence: float | None,
    activity_type: str,
) -> tuple[bool, float | None, float, str, UUID | None]:
    is_correct, score = evaluate_answer(
        database, session.user_id, question, selected_option_id, answer_text, response_time_seconds, hints_used, confidence,
    )
    if question.concept_id is None or score is None:
        return is_correct, score, 0.0, "in_progress", None

    progress = get_or_create_progress(database, session.id, question.concept_id, score)
    path = path_items(database, session.user_id, session.target_concept_id)
    next_id = current_concept_id(path)
    if activity_type == "understanding_check" and score >= MASTERY_THRESHOLD:
        progress.status = "completed"
    session.current_concept_id = next_id
    if next_id is None:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
    database.commit()
    return is_correct, score, float(progress.completion_percent), progress.status, next_id