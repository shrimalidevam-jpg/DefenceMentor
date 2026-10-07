"""Transparent, configurable mastery scoring for Phase 10."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.learning import StudentMastery
from app.models.questions import Question, QuestionAttempt


DIFFICULTY_WEIGHTS = {"easy": 0.8, "medium": 1.0, "hard": 1.2}
EXPECTED_RESPONSE_SECONDS = {"easy": 45, "medium": 75, "hard": 120}


def _attempt_weight(attempt: QuestionAttempt, question: Question, position: int, total: int) -> float:
    difficulty = question.difficulty.value
    weight = DIFFICULTY_WEIGHTS[difficulty]
    if attempt.response_time_seconds is not None:
        expected = EXPECTED_RESPONSE_SECONDS[difficulty]
        time_ratio = max(0.0, (attempt.response_time_seconds - expected) / expected)
        weight *= max(0.7, 1.0 - (time_ratio * 0.3))
    weight *= max(0.6, 1.0 - (attempt.hints_used * 0.1))
    if attempt.confidence is not None:
        confidence = float(attempt.confidence)
        weight *= (0.9 + (0.1 * confidence)) if attempt.is_correct else (1.1 - (0.2 * confidence))
    recency = 1.0 + (settings.MASTERY_RECENCY_WEIGHT * (position / max(total, 1)))
    return weight * recency


def calculate_mastery_score(database: Session, user_id: UUID, concept_id: UUID) -> float:
    attempts = list(
        database.execute(
            select(QuestionAttempt, Question)
            .join(Question, Question.id == QuestionAttempt.question_id)
            .where(QuestionAttempt.user_id == user_id, Question.concept_id == concept_id)
            .order_by(QuestionAttempt.attempted_at)
        ).all()
    )
    if not attempts:
        return 0.0
    weighted_score = 0.0
    total_weight = 0.0
    for position, (attempt, question) in enumerate(attempts, start=1):
        weight = _attempt_weight(attempt, question, position, len(attempts))
        weighted_score += (100.0 if attempt.is_correct else 0.0) * weight
        total_weight += weight
    return round(weighted_score / total_weight, 2) if total_weight else 0.0


def update_mastery(database: Session, user_id: UUID, concept_id: UUID) -> float:
    score = calculate_mastery_score(database, user_id, concept_id)
    mastery = database.scalar(
        select(StudentMastery).where(
            StudentMastery.user_id == user_id,
            StudentMastery.concept_id == concept_id,
        )
    )
    if mastery is None:
        mastery = StudentMastery(user_id=user_id, concept_id=concept_id)
        database.add(mastery)
    mastery.score = score
    mastery.last_evaluated_at = datetime.now(timezone.utc)
    return score


def mastery_summary(database: Session, user_id: UUID, concept_id: UUID) -> dict:
    score = calculate_mastery_score(database, user_id, concept_id)
    total = database.scalar(
        select(func.count(QuestionAttempt.id))
        .join(Question, Question.id == QuestionAttempt.question_id)
        .where(QuestionAttempt.user_id == user_id, Question.concept_id == concept_id)
    ) or 0
    correct = database.scalar(
        select(func.count(QuestionAttempt.id))
        .join(Question, Question.id == QuestionAttempt.question_id)
        .where(
            QuestionAttempt.user_id == user_id,
            Question.concept_id == concept_id,
            QuestionAttempt.is_correct.is_(True),
        )
    ) or 0
    average_time = database.scalar(
        select(func.avg(QuestionAttempt.response_time_seconds))
        .join(Question, Question.id == QuestionAttempt.question_id)
        .where(QuestionAttempt.user_id == user_id, Question.concept_id == concept_id)
    )
    hints = database.scalar(
        select(func.coalesce(func.sum(QuestionAttempt.hints_used), 0))
        .join(Question, Question.id == QuestionAttempt.question_id)
        .where(QuestionAttempt.user_id == user_id, Question.concept_id == concept_id)
    ) or 0
    return {
        "concept_id": concept_id,
        "mastery_score": score,
        "status": "mastered" if score >= settings.MASTERY_THRESHOLD else "developing",
        "attempt_count": int(total),
        "correct_count": int(correct),
        "accuracy": round((correct / total) * 100, 2) if total else 0.0,
        "average_response_time_seconds": round(float(average_time), 2) if average_time is not None else None,
        "hints_used": int(hints),
    }