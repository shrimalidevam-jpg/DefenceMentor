"""Personalized daily study plans based on curriculum and mastery evidence."""

from datetime import date, datetime, time, timedelta, timezone
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.clock import india_today
from app.core.config import settings
from app.core.database import get_db
from app.models.curriculum import Chapter, Concept, Exam, Subject, Topic
from app.models.learning import StudentMastery
from app.models.study_planner import StudyPlanTask
from app.models.daily_review import DailyReviewAttempt
from app.models.users import StudentProfile, User
from app.schemas.study_planner import StudyCalendarDay, StudyCalendarExam, StudyCalendarResponse, StudyCalendarTask, StudyPlanResponse, StudyPlanTaskResponse, StudyPlanTaskUpdate, StudyPlannerPreferences, StudyPlannerPreferencesUpdate, StudyScheduleBlock


router = APIRouter(prefix="/study-planner", tags=["Study planner"])


def _selected_subjects(profile: StudentProfile) -> list[str]:
    try:
        subjects = json.loads(profile.study_subjects or "[]")
    except (TypeError, json.JSONDecodeError):
        subjects = []
    return [code for code in subjects if code in {"MATH", "GAT"}]


def _target_task_count(profile: StudentProfile) -> int:
    return max(1, (profile.daily_study_minutes + profile.focus_session_minutes - 1) // profile.focus_session_minutes)


def _candidate_query(user: User, profile: StudentProfile):
    """Build the shared ordered curriculum/mastery candidate query."""
    query = (
        select(Concept, Subject, StudentMastery.score)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .join(Exam, Exam.id == Subject.exam_id)
        .outerjoin(StudentMastery, (StudentMastery.concept_id == Concept.id) & (StudentMastery.user_id == user.id))
        .where(Exam.is_active.is_(True), Subject.code.in_(_selected_subjects(profile)))
        .order_by(func.coalesce(StudentMastery.score, 0), Subject.display_order, Chapter.display_order, Topic.display_order, Concept.display_order)
    )
    exam_code = profile.exam_target.split()[0].upper()
    return query.where(Exam.code == exam_code) if exam_code else query


def _select_candidates(rows: list[tuple[Concept, Subject, object]], count: int, profile: StudentProfile) -> list[tuple[Concept, Subject, object]]:
    subjects = _selected_subjects(profile)
    if len(subjects) < 2:
        return rows[:count]
    math_rows = [row for row in rows if row[1].code == "MATH"]
    gat_rows = [row for row in rows if row[1].code == "GAT"]
    math_target = round(count * profile.math_share_percent / 100)
    gat_target = count - math_target
    math_selected = math_rows[:math_target]
    gat_selected = gat_rows[:gat_target]
    selected: list[tuple[Concept, Subject, object]] = []
    math_index = gat_index = 0
    while math_index < len(math_selected) or gat_index < len(gat_selected):
        choose_math = gat_index >= len(gat_selected) or (
            math_index < len(math_selected)
            and (math_index + 1) / max(math_target, 1) <= (gat_index + 1) / max(gat_target, 1)
        )
        if choose_math:
            selected.append(math_selected[math_index])
            math_index += 1
        else:
            selected.append(gat_selected[gat_index])
            gat_index += 1
    selected_ids = {row[0].id for row in selected}
    if len(selected) < count:
        selected.extend(row for row in rows if row[0].id not in selected_ids)
    return selected[:count]


def _student_profile(database: Session, user: User) -> StudentProfile:
    profile = database.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return profile


def _tomorrow(today: date) -> date:
    return today + timedelta(days=1)


def _task_type(score: object) -> str:
    mastery_score = float(score) if score is not None else None
    return "learn" if mastery_score is None else "revise" if mastery_score < settings.MASTERY_THRESHOLD else "practice"


def _add_plan_task(database: Session, user: User, profile: StudentProfile, plan_date: date, concept: Concept, score: object, order: int) -> None:
    task_type = _task_type(score)
    database.add(StudyPlanTask(
        user_id=user.id,
        plan_date=plan_date,
        concept_id=concept.id,
        task_type=task_type,
        estimated_minutes=min(profile.focus_session_minutes, profile.daily_study_minutes - (order - 1) * profile.focus_session_minutes),
        display_order=order,
    ))


def _generate_today(database: Session, user: User, profile: StudentProfile, today: date) -> None:
    existing_rows = list(database.scalars(select(StudyPlanTask).where(StudyPlanTask.user_id == user.id, StudyPlanTask.plan_date == today).order_by(StudyPlanTask.display_order)).all())
    existing_concepts = {task.concept_id for task in existing_rows}
    remaining_minutes = max(0, profile.daily_study_minutes - sum(task.estimated_minutes for task in existing_rows if task.is_completed))
    already_planned_minutes = sum(task.estimated_minutes for task in existing_rows if not task.is_completed)
    unplanned_minutes = max(0, remaining_minutes - already_planned_minutes)
    missing_count = (unplanned_minutes + profile.focus_session_minutes - 1) // profile.focus_session_minutes
    candidates = database.execute(_candidate_query(user, profile)).all()
    selected = _select_candidates([row for row in candidates if row[0].id not in existing_concepts], missing_count, profile)
    next_order = max((task.display_order for task in existing_rows), default=0) + 1
    for order, (concept, subject, score) in enumerate(selected, start=next_order):
        _add_plan_task(database, user, profile, today, concept, score, order)
    database.flush()
    today_tasks = list(database.scalars(select(StudyPlanTask).where(StudyPlanTask.user_id == user.id, StudyPlanTask.plan_date == today).order_by(StudyPlanTask.display_order)).all())
    remaining_minutes = max(0, profile.daily_study_minutes - sum(task.estimated_minutes for task in today_tasks if task.is_completed))
    for task in today_tasks:
        if task.is_completed:
            continue
        task.estimated_minutes = min(profile.focus_session_minutes, remaining_minutes)
        remaining_minutes -= task.estimated_minutes
    database.commit()


def _generate_tomorrow(database: Session, user: User, profile: StudentProfile, today: date) -> None:
    tomorrow = _tomorrow(today)
    candidates = list(database.execute(_candidate_query(user, profile)).all())
    today_rows = database.execute(
        select(StudyPlanTask, Concept, Subject, StudentMastery.score)
        .join(Concept, Concept.id == StudyPlanTask.concept_id)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .outerjoin(StudentMastery, (StudentMastery.concept_id == Concept.id) & (StudentMastery.user_id == user.id))
        .where(StudyPlanTask.user_id == user.id, StudyPlanTask.plan_date == today)
        .order_by(StudyPlanTask.display_order)
    ).all()

    selected_ids: set[UUID] = set()
    target_count = _target_task_count(profile)
    selected: list[tuple[Concept, object]] = []
    for task, concept, subject, score in today_rows:
        if not task.is_completed and subject.code in _selected_subjects(profile) and concept.id not in selected_ids:
            selected.append((concept, score))
            selected_ids.add(concept.id)
            if len(selected) == target_count:
                break

    today_concept_ids = {concept.id for _task, concept, _subject, _score in today_rows}
    remaining_candidates = [row for row in candidates if row[0].id not in today_concept_ids and row[0].id not in selected_ids]
    selected_candidates = _select_candidates(remaining_candidates, target_count - len(selected), profile)
    for concept, _subject, score in selected_candidates:
        if len(selected) == target_count:
            break
        if concept.id not in today_concept_ids and concept.id not in selected_ids:
            selected.append((concept, score))
            selected_ids.add(concept.id)

    if len(selected) < target_count:
        for _task, concept, subject, score in today_rows:
            if len(selected) == target_count:
                break
            mastery_score = float(score) if score is not None else None
            if subject.code in _selected_subjects(profile) and concept.id not in selected_ids and (mastery_score is None or mastery_score < settings.MASTERY_THRESHOLD):
                selected.append((concept, score))
                selected_ids.add(concept.id)

    for order, (concept, score) in enumerate(selected, start=1):
        _add_plan_task(database, user, profile, tomorrow, concept, score, order)
    database.commit()


def _build_schedule(tasks: list[StudyPlanTaskResponse], profile: StudentProfile) -> list[StudyScheduleBlock]:
    cursor = datetime.combine(date.today(), time.fromisoformat(profile.study_start_time))
    blocks: list[StudyScheduleBlock] = []
    focus_count = 0
    for task in tasks:
        duration = task.estimated_minutes
        end = cursor + timedelta(minutes=duration)
        blocks.append(StudyScheduleBlock(
            kind="focus", label={"learn": "Learn a new concept", "revise": "Review a weak topic", "practice": "Practice and recall"}.get(task.task_type, "Study session"),
            start_time=cursor.strftime("%H:%M"), end_time=end.strftime("%H:%M"), duration_minutes=duration,
            task_id=task.id, concept_name=task.concept_name, subject_name=task.subject_name, is_completed=task.is_completed,
        ))
        cursor = end
        focus_count += 1
        if focus_count >= len(tasks):
            continue
        # Add a proper meal break around midday, while leaving the schedule flexible.
        if focus_count == 3 and time(11, 0) <= cursor.time() <= time(14, 0):
            meal_end = cursor + timedelta(minutes=45)
            blocks.append(StudyScheduleBlock(kind="meal", label="Lunch and reset", start_time=cursor.strftime("%H:%M"), end_time=meal_end.strftime("%H:%M"), duration_minutes=45))
            cursor = meal_end
        else:
            break_end = cursor + timedelta(minutes=profile.break_minutes)
            blocks.append(StudyScheduleBlock(kind="break", label="Rest your eyes and move", start_time=cursor.strftime("%H:%M"), end_time=break_end.strftime("%H:%M"), duration_minutes=profile.break_minutes))
            cursor = break_end
    return blocks


def _plan_response(database: Session, user: User, profile: StudentProfile, today: date) -> StudyPlanResponse:
    task_rows = database.execute(
        select(StudyPlanTask, Concept, Subject, StudentMastery.score)
        .join(Concept, Concept.id == StudyPlanTask.concept_id)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .outerjoin(StudentMastery, (StudentMastery.concept_id == Concept.id) & (StudentMastery.user_id == user.id))
        .where(StudyPlanTask.user_id == user.id, StudyPlanTask.plan_date == today)
        .order_by(StudyPlanTask.display_order)
    ).all()
    target_date = profile.target_exam_date
    days_to_exam = (target_date - today).days if target_date else None
    task_responses = [
        StudyPlanTaskResponse(
            id=task.id,
            plan_date=task.plan_date,
            concept_id=concept.id,
            concept_name=concept.name,
            subject_name=subject.name,
            task_type=task.task_type,
            estimated_minutes=task.estimated_minutes,
            display_order=task.display_order,
            mastery_score=float(score) if score is not None else None,
        is_completed=task.is_completed,
            completed_at=task.completed_at,
        )
        for task, concept, subject, score in task_rows
    ]
    return StudyPlanResponse(
        plan_date=today,
        exam_target=profile.exam_target,
        target_exam_date=target_date,
        days_to_exam=days_to_exam,
        total_minutes=sum(task.estimated_minutes for task in task_responses),
        completed_count=sum(1 for task in task_responses if task.is_completed),
        tasks=task_responses,
        schedule=_build_schedule(task_responses, profile),
    )


def _empty_plan(profile: StudentProfile, plan_date: date) -> StudyPlanResponse:
    days_to_exam = (profile.target_exam_date - plan_date).days if profile.target_exam_date else None
    return StudyPlanResponse(
        plan_date=plan_date, exam_target=profile.exam_target, target_exam_date=profile.target_exam_date,
        days_to_exam=days_to_exam, total_minutes=0, completed_count=0, tasks=[], schedule=[],
    )


def _preferences_response(profile: StudentProfile) -> StudyPlannerPreferences:
    return StudyPlannerPreferences(
        planner_setup_complete=profile.planner_setup_complete,
        daily_study_minutes=profile.daily_study_minutes,
        study_start_time=profile.study_start_time,
        focus_session_minutes=profile.focus_session_minutes,
        break_minutes=profile.break_minutes,
        study_subjects=_selected_subjects(profile),
        math_share_percent=profile.math_share_percent,
    )


@router.get("/preferences", response_model=StudyPlannerPreferences)
def get_preferences(current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> StudyPlannerPreferences:
    profile = _student_profile(database, current_user)
    return _preferences_response(profile)


@router.put("/preferences", response_model=StudyPlannerPreferences)
def update_preferences(payload: StudyPlannerPreferencesUpdate, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> StudyPlannerPreferences:
    profile = _student_profile(database, current_user)
    for field_name, value in payload.model_dump(exclude={"study_subjects"}).items():
        setattr(profile, field_name, value)
    profile.study_subjects = json.dumps(payload.study_subjects)
    profile.planner_setup_complete = True
    database.commit()
    database.refresh(profile)
    today = india_today()
    database.execute(delete(StudyPlanTask).where(
        StudyPlanTask.user_id == current_user.id,
        StudyPlanTask.plan_date == today,
        StudyPlanTask.concept_id.in_(
            select(Concept.id)
            .join(Topic, Topic.id == Concept.topic_id)
            .join(Chapter, Chapter.id == Topic.chapter_id)
            .join(Subject, Subject.id == Chapter.subject_id)
            .where(Subject.code.not_in(payload.study_subjects))
        ),
    ))
    database.execute(delete(StudyPlanTask).where(
        StudyPlanTask.user_id == current_user.id,
        StudyPlanTask.plan_date == today,
        StudyPlanTask.is_completed.is_(False),
    ))
    database.execute(delete(StudyPlanTask).where(
        StudyPlanTask.user_id == current_user.id,
        StudyPlanTask.plan_date == _tomorrow(today),
    ))
    database.commit()
    _generate_today(database, current_user, profile, today)
    _generate_tomorrow(database, current_user, profile, today)
    return _preferences_response(profile)


@router.get("/today", response_model=StudyPlanResponse)
def get_today_plan(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> StudyPlanResponse:
    profile = _student_profile(database, current_user)
    today = india_today()
    if not profile.planner_setup_complete or not _selected_subjects(profile):
        return _empty_plan(profile, today)
    _generate_today(database, current_user, profile, today)
    return _plan_response(database, current_user, profile, today)


@router.get("/tomorrow", response_model=StudyPlanResponse)
def get_tomorrow_plan(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> StudyPlanResponse:
    profile = _student_profile(database, current_user)
    today = india_today()
    tomorrow = _tomorrow(today)
    if not profile.planner_setup_complete or not _selected_subjects(profile):
        return _empty_plan(profile, tomorrow)
    existing = database.scalar(select(StudyPlanTask.id).where(StudyPlanTask.user_id == current_user.id, StudyPlanTask.plan_date == tomorrow).limit(1))
    if existing is None:
        _generate_tomorrow(database, current_user, profile, today)
    return _plan_response(database, current_user, profile, tomorrow)


@router.get("/calendar", response_model=StudyCalendarResponse)
def get_study_calendar(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> StudyCalendarResponse:
    """Return saved study tasks and revision attempts for one calendar month."""
    start = date.fromisoformat(f"{month}-01")
    end = date(start.year + (start.month == 12), 1 if start.month == 12 else start.month + 1, 1)
    task_rows = database.execute(
        select(StudyPlanTask, Concept, Subject)
        .join(Concept, Concept.id == StudyPlanTask.concept_id)
        .join(Topic, Topic.id == Concept.topic_id)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .join(Subject, Subject.id == Chapter.subject_id)
        .where(StudyPlanTask.user_id == current_user.id, StudyPlanTask.plan_date >= start, StudyPlanTask.plan_date < end)
        .order_by(StudyPlanTask.plan_date, StudyPlanTask.display_order)
    ).all()
    attempts = database.scalars(
        select(DailyReviewAttempt)
        .where(DailyReviewAttempt.user_id == current_user.id, DailyReviewAttempt.plan_date >= start, DailyReviewAttempt.plan_date < end)
        .order_by(DailyReviewAttempt.plan_date, DailyReviewAttempt.attempt_no)
    ).all()

    tasks_by_day: dict[date, list[StudyCalendarTask]] = {}
    exams_by_day: dict[date, list[StudyCalendarExam]] = {}
    for task, concept, subject in task_rows:
        tasks_by_day.setdefault(task.plan_date, []).append(StudyCalendarTask(
            id=task.id, concept_name=concept.name, subject_name=subject.name,
            task_type=task.task_type, estimated_minutes=task.estimated_minutes,
            is_completed=task.is_completed, completed_at=task.completed_at,
        ))
    for attempt in attempts:
        completed = attempt.status == "completed"
        exams_by_day.setdefault(attempt.plan_date, []).append(StudyCalendarExam(
            id=attempt.id, attempt_no=attempt.attempt_no, status=attempt.status,
            question_count=attempt.question_count, answered_count=attempt.answered_count,
            correct_answers=attempt.correct_answers if completed else 0,
            score_marks=attempt.correct_answers if completed else 0,
            max_marks=attempt.question_count, score_percent=float(attempt.score) if completed and attempt.score is not None else None,
            completed_at=attempt.completed_at,
        ))

    activity_dates = sorted(set(tasks_by_day) | set(exams_by_day))
    days = []
    for plan_date in activity_dates:
        tasks = tasks_by_day.get(plan_date, [])
        days.append(StudyCalendarDay(
            plan_date=plan_date,
            total_minutes=sum(task.estimated_minutes for task in tasks),
            completed_minutes=sum(task.estimated_minutes for task in tasks if task.is_completed),
            completed_count=sum(1 for task in tasks if task.is_completed),
            tasks=tasks,
            exams=exams_by_day.get(plan_date, []),
        ))
    return StudyCalendarResponse(month=month, days=days)


@router.post("/tomorrow/regenerate", response_model=StudyPlanResponse)
def regenerate_tomorrow_plan(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> StudyPlanResponse:
    profile = _student_profile(database, current_user)
    today = india_today()
    tomorrow = _tomorrow(today)
    if not profile.planner_setup_complete or not _selected_subjects(profile):
        return _empty_plan(profile, tomorrow)
    database.execute(delete(StudyPlanTask).where(StudyPlanTask.user_id == current_user.id, StudyPlanTask.plan_date == tomorrow))
    database.commit()
    _generate_tomorrow(database, current_user, profile, today)
    return _plan_response(database, current_user, profile, tomorrow)


@router.patch("/tasks/{task_id}", response_model=StudyPlanResponse)
def update_task(
    task_id: UUID,
    payload: StudyPlanTaskUpdate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> StudyPlanResponse:
    task = database.scalar(select(StudyPlanTask).where(StudyPlanTask.id == task_id, StudyPlanTask.user_id == current_user.id))
    if task is None:
        raise HTTPException(status_code=404, detail="Study task not found")
    if task.plan_date > india_today():
        raise HTTPException(status_code=409, detail="Future study tasks cannot be marked complete yet")
    task.is_completed = payload.is_completed
    task.completed_at = datetime.now(timezone.utc) if payload.is_completed else None
    database.commit()
    profile = _student_profile(database, current_user)
    return _plan_response(database, current_user, profile, task.plan_date)
