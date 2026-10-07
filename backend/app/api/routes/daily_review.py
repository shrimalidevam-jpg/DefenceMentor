"""Short daily revision tests from topics the student completed today."""

from datetime import date, datetime, timedelta, timezone
import random
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.clock import india_today
from app.core.database import get_db
from app.models.curriculum import Chapter, Concept, Subject, Topic
from app.models.daily_review import DailyReviewAttempt, DailyReviewItem
from app.models.questions import Question, QuestionAnswer, QuestionAttempt, QuestionOption
from app.models.study_planner import StudyPlanTask
from app.models.users import StudentProfile, User
from app.schemas.daily_review import (
    DailyReviewAnswerRequest,
    DailyReviewAnswerResponse,
    DailyReviewOptionResponse,
    DailyReviewQuestionResponse,
    DailyReviewResponse,
)
from app.utils.questions import get_question_option


router = APIRouter(prefix="/daily-review", tags=["Daily revision test"])
QUESTION_LIMIT = 15


def _question_response(database: Session, attempt: DailyReviewAttempt) -> DailyReviewQuestionResponse | None:
    item = database.scalar(
        select(DailyReviewItem).where(
            DailyReviewItem.attempt_id == attempt.id,
            DailyReviewItem.position == attempt.answered_count + 1,
        )
    )
    if item is None:
        return None
    question = database.get(Question, item.question_id)
    if question is None:
        return None
    options = list(database.scalars(select(QuestionOption).where(QuestionOption.question_id == question.id).order_by(QuestionOption.display_order)))
    return DailyReviewQuestionResponse(
        id=question.id,
        prompt=question.prompt,
        difficulty=question.difficulty.value,
        question_number=item.position,
        total_questions=attempt.question_count,
        options=[DailyReviewOptionResponse.model_validate(option, from_attributes=True) for option in options],
    )


def _attempt_response(database: Session, attempt: DailyReviewAttempt) -> DailyReviewResponse:
    completed = attempt.status == "completed"
    return DailyReviewResponse(
        id=attempt.id,
        plan_date=attempt.plan_date,
        attempt_no=attempt.attempt_no,
        status=attempt.status,
        answered_count=attempt.answered_count,
        question_count=attempt.question_count,
        correct_answers=attempt.correct_answers if completed else 0,
        score=float(attempt.score) if completed and attempt.score is not None else None,
        score_marks=attempt.correct_answers if completed else 0,
        max_marks=attempt.question_count,
        question=_question_response(database, attempt) if attempt.status == "in_progress" else None,
    )


def _start_review(plan_date: date, retake: bool, current_user: User, database: Session) -> DailyReviewResponse:
    today = india_today()
    if plan_date not in {today, today + timedelta(days=1)}:
        raise HTTPException(status_code=422, detail="A revision exam can only be started for today or tomorrow")

    existing = database.scalar(
        select(DailyReviewAttempt)
        .where(DailyReviewAttempt.user_id == current_user.id, DailyReviewAttempt.plan_date == plan_date)
        .order_by(DailyReviewAttempt.attempt_no.desc())
    )
    if existing is not None and existing.status == "in_progress" and existing.question_count == QUESTION_LIMIT:
        return _attempt_response(database, existing)
    if existing is not None and existing.status == "in_progress":
        existing.status = "superseded"
        existing.completed_at = datetime.now(timezone.utc)
        database.commit()
    if existing is not None and not retake and existing.question_count == QUESTION_LIMIT:
        return _attempt_response(database, existing)

    task_query = select(StudyPlanTask.concept_id).where(
        StudyPlanTask.user_id == current_user.id,
        StudyPlanTask.plan_date == plan_date,
    )
    if plan_date == today:
        task_query = task_query.where(StudyPlanTask.is_completed.is_(True))
    planned_concept_ids = list(database.scalars(task_query))
    if not planned_concept_ids:
        day_label = "today's completed" if plan_date == today else "tomorrow's planned"
        raise HTTPException(status_code=409, detail=f"There are no topics in {day_label} study plan yet")

    subject_query = (
        select(Subject.id, Subject.code)
        .select_from(StudyPlanTask)
        .join(Concept, Concept.id == StudyPlanTask.concept_id)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .where(StudyPlanTask.user_id == current_user.id, StudyPlanTask.plan_date == plan_date)
        .distinct()
    )
    if plan_date == today:
        subject_query = subject_query.where(StudyPlanTask.is_completed.is_(True))
    planned_subjects = list(database.execute(subject_query).all())
    candidates_by_subject: dict[UUID, list[Question]] = {}
    for subject_id, _code in planned_subjects:
        candidates_by_subject[subject_id] = list(database.scalars(
            select(Question)
            .join(QuestionAnswer, QuestionAnswer.question_id == Question.id)
            .join(QuestionOption, (QuestionOption.id == QuestionAnswer.correct_option_id) & (QuestionOption.question_id == Question.id))
            .where(Question.subject_id == subject_id, Question.is_published.is_(True))
            .order_by(case((Question.concept_id.in_(planned_concept_ids), 0), else_=1), func.random())
        ))
    candidate_ids = [question.id for rows in candidates_by_subject.values() for question in rows]
    option_counts = dict(database.execute(
        select(QuestionOption.question_id, func.count(QuestionOption.id))
        .where(QuestionOption.question_id.in_(candidate_ids))
        .group_by(QuestionOption.question_id)
    ).all()) if candidate_ids else {}
    for subject_id in candidates_by_subject:
        candidates_by_subject[subject_id] = [q for q in candidates_by_subject[subject_id] if option_counts.get(q.id, 0) >= 2]

    usable_subjects = [(subject_id, code) for subject_id, code in planned_subjects if candidates_by_subject.get(subject_id)]
    profile = database.scalar(select(StudentProfile).where(StudentProfile.user_id == current_user.id))
    if len(usable_subjects) == 1:
        desired_counts = {usable_subjects[0][0]: QUESTION_LIMIT}
    else:
        math_share = profile.math_share_percent if profile is not None else 50
        math_count = round(QUESTION_LIMIT * math_share / 100)
        desired_counts = {subject_id: (math_count if code == "MATH" else QUESTION_LIMIT - math_count) for subject_id, code in usable_subjects}
    questions: list[Question] = []
    for subject_id, _code in usable_subjects:
        questions.extend(candidates_by_subject[subject_id][:desired_counts[subject_id]])
    selected_ids = {question.id for question in questions}
    if len(questions) < QUESTION_LIMIT:
        overflow = [q for subject_id, _code in usable_subjects for q in candidates_by_subject[subject_id] if q.id not in selected_ids]
        questions.extend(overflow[:QUESTION_LIMIT - len(questions)])
    questions = questions[:QUESTION_LIMIT]
    if len(questions) < QUESTION_LIMIT:
        raise HTTPException(
            status_code=409,
            detail=f"This 15-mark exam needs 15 published questions from the selected subjects. {len(questions)} are available right now.",
        )
    random.shuffle(questions)

    latest_attempt_no = database.scalar(select(func.max(DailyReviewAttempt.attempt_no)).where(
        DailyReviewAttempt.user_id == current_user.id,
        DailyReviewAttempt.plan_date == plan_date,
    )) or 0
    attempt = DailyReviewAttempt(
        user_id=current_user.id,
        plan_date=plan_date,
        attempt_no=latest_attempt_no + 1,
        question_count=QUESTION_LIMIT,
    )
    database.add(attempt)
    database.flush()
    database.add_all([
        DailyReviewItem(attempt_id=attempt.id, question_id=question.id, position=position)
        for position, question in enumerate(questions, start=1)
    ])
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        latest = database.scalar(
            select(DailyReviewAttempt)
            .where(DailyReviewAttempt.user_id == current_user.id, DailyReviewAttempt.plan_date == plan_date)
            .order_by(DailyReviewAttempt.attempt_no.desc())
        )
        if latest is not None:
            return _attempt_response(database, latest)
        raise
    database.refresh(attempt)
    return _attempt_response(database, attempt)


@router.post("/today/start", response_model=DailyReviewResponse, status_code=201)
def start_today_review(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DailyReviewResponse:
    return _start_review(india_today(), False, current_user, database)


@router.post("/date/{plan_date}/start", response_model=DailyReviewResponse, status_code=201)
def start_planned_review(
    plan_date: date,
    retake: bool = False,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DailyReviewResponse:
    return _start_review(plan_date, retake, current_user, database)


@router.post("/{attempt_id}/answer", response_model=DailyReviewAnswerResponse)
def answer_review_question(
    attempt_id: UUID,
    payload: DailyReviewAnswerRequest,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DailyReviewAnswerResponse:
    attempt = database.scalar(select(DailyReviewAttempt).where(DailyReviewAttempt.id == attempt_id, DailyReviewAttempt.user_id == current_user.id).with_for_update())
    if attempt is None:
        raise HTTPException(status_code=404, detail="Daily revision test not found")
    if attempt.status != "in_progress":
        raise HTTPException(status_code=409, detail="This daily revision test is already complete")

    item = database.scalar(select(DailyReviewItem).where(
        DailyReviewItem.attempt_id == attempt.id,
        DailyReviewItem.position == attempt.answered_count + 1,
    ))
    if item is None or item.question_id != payload.question_id:
        raise HTTPException(status_code=409, detail="This is not the current revision question")
    option = get_question_option(database, item.question_id, payload.selected_option_id)
    question = database.get(Question, item.question_id)
    answer = database.scalar(select(QuestionAnswer).where(QuestionAnswer.question_id == item.question_id))
    if question is None or answer is None or answer.correct_option_id is None:
        raise HTTPException(status_code=422, detail="This revision question has no configured correct option")

    is_correct = option.id == answer.correct_option_id
    now = datetime.now(timezone.utc)
    item.selected_option_id = option.id
    item.is_correct = is_correct
    item.answered_at = now
    attempt.answered_count += 1
    attempt.correct_answers += int(is_correct)
    database.add(QuestionAttempt(
        user_id=current_user.id,
        question_id=question.id,
        selected_option_id=option.id,
        is_correct=is_correct,
        assessment_round="daily_review",
        attempted_at=now,
    ))
    completed = attempt.answered_count == attempt.question_count
    if completed:
        attempt.status = "completed"
        attempt.completed_at = now
        attempt.score = round(attempt.correct_answers / attempt.question_count * 100, 2)
    database.commit()
    database.refresh(attempt)
    return DailyReviewAnswerResponse(
        is_correct=is_correct if completed else None,
        explanation=question.explanation if completed else None,
        answered_count=attempt.answered_count,
        correct_answers=attempt.correct_answers if completed else 0,
        completed=completed,
        score=float(attempt.score) if attempt.score is not None else None,
        score_marks=attempt.correct_answers if completed else 0,
        max_marks=attempt.question_count,
        next_question=_question_response(database, attempt) if not completed else None,
    )
