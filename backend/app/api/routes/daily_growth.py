"""Daily vocabulary quiz and SSB preparation tip endpoints."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.clock import india_today
from app.core.database import get_db
from app.models.daily_vocabulary import DailyVocabularyAttempt
from app.models.users import User
from app.schemas.daily_growth import (
    DailyGrowthResponse,
    VocabularyAnswerRequest,
    VocabularyAnswerResponse,
    VocabularyQuestionResponse,
)
from app.services.daily_growth import VocabularyQuestion, today_ssb_tip, today_vocabulary


router = APIRouter(prefix="/daily-growth", tags=["Daily vocabulary and SSB"])


def _question_response(question: VocabularyQuestion, attempt: DailyVocabularyAttempt | None = None) -> VocabularyQuestionResponse:
    return VocabularyQuestionResponse(
        id=question.id,
        word=question.word,
        options={letter: text for letter, text in zip("ABCD", question.options)},
        explanation=question.meaning if attempt else None,
        example=question.example if attempt else None,
        selected_option=attempt.selected_option if attempt else None,
        correct_option=question.correct_option if attempt else None,
        is_correct=attempt.is_correct if attempt else None,
    )


def _daily_response(database: Session, user: User, today: date) -> DailyGrowthResponse:
    questions = today_vocabulary(today)
    attempts = list(database.scalars(select(DailyVocabularyAttempt).where(
        DailyVocabularyAttempt.user_id == user.id,
        DailyVocabularyAttempt.practice_date == today,
    )))
    attempts_by_word = {attempt.word_id: attempt for attempt in attempts}
    correct_count = sum(1 for attempt in attempts if attempt.is_correct)
    tip_title, tip_content, category = today_ssb_tip(today)
    return DailyGrowthResponse(
        practice_date=today,
        questions=[_question_response(question, attempts_by_word.get(question.id)) for question in questions],
        answered_count=len(attempts),
        correct_count=correct_count,
        score_percent=round(correct_count / len(attempts) * 100, 2) if attempts else None,
        ssb_tip=f"{tip_title}: {tip_content}",
        ssb_category=category,
    )


@router.get("/today", response_model=DailyGrowthResponse)
def get_daily_growth(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DailyGrowthResponse:
    return _daily_response(database, current_user, india_today())


@router.post("/vocabulary/answer", response_model=VocabularyAnswerResponse)
def answer_vocabulary(
    payload: VocabularyAnswerRequest,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> VocabularyAnswerResponse:
    today = india_today()
    question = next((item for item in today_vocabulary(today) if item.id == payload.word_id), None)
    if question is None:
        raise HTTPException(status_code=404, detail="This word is not part of today's vocabulary set")
    existing = database.scalar(select(DailyVocabularyAttempt).where(
        DailyVocabularyAttempt.user_id == current_user.id,
        DailyVocabularyAttempt.practice_date == today,
        DailyVocabularyAttempt.word_id == question.id,
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already answered this word today")

    is_correct = payload.selected_option == question.correct_option
    answered_at = datetime.now(timezone.utc)
    database.add(DailyVocabularyAttempt(
        user_id=current_user.id,
        practice_date=today,
        word_id=question.id,
        selected_option=payload.selected_option,
        is_correct=is_correct,
        answered_at=answered_at,
    ))
    database.commit()
    answered_count = database.scalar(select(func.count(DailyVocabularyAttempt.id)).where(
        DailyVocabularyAttempt.user_id == current_user.id,
        DailyVocabularyAttempt.practice_date == today,
    )) or 0
    correct_count = database.scalar(select(func.count(DailyVocabularyAttempt.id)).where(
        DailyVocabularyAttempt.user_id == current_user.id,
        DailyVocabularyAttempt.practice_date == today,
        DailyVocabularyAttempt.is_correct.is_(True),
    )) or 0
    return VocabularyAnswerResponse(
        word_id=question.id,
        is_correct=is_correct,
        correct_option=question.correct_option,
        meaning=question.meaning,
        example=question.example,
        answered_count=int(answered_count),
        correct_count=int(correct_count),
        score_percent=round(correct_count / answered_count * 100, 2),
        answered_at=answered_at,
    )
