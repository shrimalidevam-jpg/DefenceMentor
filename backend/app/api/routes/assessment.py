"""Adaptive examination endpoints for Phase 11."""

from datetime import datetime, timedelta, timezone
import random
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.clock import INDIA_TIMEZONE
from app.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestionAssignment
from app.models.curriculum import Chapter, Subject, Topic
from app.models.enums import AttemptStatus, Difficulty, QuestionType
from app.models.questions import Question, QuestionAnswer, QuestionAttempt, QuestionOption
from app.models.users import User
from app.schemas.assessment import AssessmentAttemptResponse, AssessmentHistoryItem, AssessmentHistoryResponse, AssessmentQuestionResponse, AssessmentReportResponse, AssessmentStartRequest, AssessmentNavigateRequest, AssessmentSubmitRequest
from app.services.adaptive_exam_engine import NDA_SECTION_QUESTIONS, NDA_SECTION_TIME_SECONDS, options, report
from app.services.ai_question_generator import generate_question_batch
from app.services.ai_provider import AIProviderError
from app.utils.questions import get_question_option


router = APIRouter(prefix="/assessments", tags=["Assessments"])
NDA_SYLLABUS_TOPICS = {
    "MATH": (
        "Algebra", "Matrices and Determinants", "Trigonometry",
        "Analytical Geometry of Two and Three Dimensions", "Differential Calculus",
        "Integral Calculus and Differential Equations", "Vector Algebra", "Statistics and Probability",
    ),
    "GAT": (
        "Spotting Errors", "Comprehension", "Selecting Words", "Synonyms", "Antonyms",
        "Sentence Improvements", "Ordering of Words in a Sentence", "Physical Properties and States of Matter",
        "Motion, Force and Work, Power and Energy", "Heat and Temperature", "Sound", "Light and Optics",
        "Magnetism", "Static and Current Electricity", "Scientific Instruments, Devices and Electrical Safety",
        "Matter, Elements and Chemical Equations", "Laws of Chemical Combination", "Air and Water",
        "Hydrogen, Oxygen, Nitrogen and Carbon Dioxide", "Oxidation and Reduction", "Acids, Bases and Salts",
        "Carbon and Its Different Forms", "Fertilizers", "Common Materials and Their Preparation",
        "Atomic Structure and Chemical Quantities", "Living and Non-living Things", "Growth and Reproduction",
        "Human Body and Health", "Food, Nutrition and the Solar System", "Eminent Scientists and Achievements",
        "Indian History, Culture and Civilisation", "Freedom Movement, Constitution and Administration",
        "Development, Social Welfare and National Integration", "Modern World and Political Ideas",
        "Earth, Coordinates and Time", "Earth's Origin, Rocks and Landforms", "Oceans and the Atmosphere",
        "Weather, Climate and Natural Regions", "Regional Geography of India", "Transport, Trade and Exports of India",
        "Recent Events in India and the World", "Prominent Personalities",
        "General Science", "History", "Geography", "Current Events",
    ),
}


def section_question_count(schedule_type: str, section: str) -> int:
    return NDA_SECTION_QUESTIONS[schedule_type][section]


def section_time_limit(schedule_type: str) -> int:
    return NDA_SECTION_TIME_SECONDS[schedule_type]


def section_answered_count(database: Session, attempt: AssessmentAttempt, section: str) -> int:
    return len(section_assignments(database, attempt, section))


def section_assignments(
    database: Session,
    attempt: AssessmentAttempt,
    section: str,
) -> list[AssessmentQuestionAssignment]:
    return list(database.scalars(
        select(AssessmentQuestionAssignment)
        .where(
            AssessmentQuestionAssignment.attempt_id == attempt.id,
            AssessmentQuestionAssignment.section_name == section,
        )
        .order_by(AssessmentQuestionAssignment.display_order)
    ))


def section_elapsed_seconds(attempt: AssessmentAttempt) -> int:
    started_at = attempt.section_started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))


def create_ai_questions(database: Session, exam_id: UUID, subject: Subject) -> list[Question]:
    topic_names = list(database.scalars(
        select(Topic.name)
        .join(Chapter, Chapter.id == Topic.chapter_id)
        .where(Chapter.subject_id == subject.id)
        .order_by(Topic.display_order, Topic.name)
    ))
    topic_choices = list(dict.fromkeys(topic_names + list(NDA_SYLLABUS_TOPICS.get(subject.code, (subject.name,)))))
    try:
        generated_questions = generate_question_batch(
            subject=subject.name,
            difficulty=random.choice([
                Difficulty.EASY.value,
                Difficulty.MEDIUM.value,
                Difficulty.HARD.value,
            ]),
            topics=topic_choices,
            count=5,
        )
    except AIProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Question bank is short and AI generation failed: {error}",
        ) from error

    database_topics = {
        name.casefold(): topic_id
        for topic_id, name in database.execute(
            select(Topic.id, Topic.name)
            .join(Chapter, Chapter.id == Topic.chapter_id)
            .where(Chapter.subject_id == subject.id)
        )
    }
    questions: list[Question] = []
    for generated in generated_questions:
        question = Question(
            exam_id=exam_id,
            subject_id=subject.id,
            topic_id=database_topics.get((generated.topic or "").casefold()),
            prompt=generated.prompt,
            explanation=generated.explanation,
            difficulty=Difficulty(generated.difficulty),
            question_type=QuestionType.MULTIPLE_CHOICE,
            tags="ai-generated",
            is_published=True,
        )
        database.add(question)
        database.flush()
        generated_options = [
            QuestionOption(question_id=question.id, text=text, display_order=index)
            for index, text in enumerate(generated.options, start=1)
        ]
        database.add_all(generated_options)
        database.flush()
        database.add(QuestionAnswer(
            question_id=question.id,
            correct_option_id=generated_options[generated.correct_option_index].id,
        ))
        questions.append(question)
    database.flush()
    return questions


def same_day_deadline(attempt: AssessmentAttempt) -> datetime:
    started_at = attempt.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    local_start = started_at.astimezone(INDIA_TIMEZONE)
    return datetime.combine(local_start.date() + timedelta(days=1), datetime.min.time(), tzinfo=INDIA_TIMEZONE)


def enforce_same_day(database: Session, attempt: AssessmentAttempt) -> None:
    if attempt.schedule_type != "monthly" or attempt.status != AttemptStatus.IN_PROGRESS:
        return
    deadline = same_day_deadline(attempt)
    if datetime.now(INDIA_TIMEZONE) >= deadline:
        attempt.status = AttemptStatus.ABANDONED
        attempt.current_question_id = None
        database.commit()
        raise HTTPException(status_code=410, detail="Monthly mock expired. Both sections must be completed on the same day.")


def choose_mock_question(database: Session, attempt: AssessmentAttempt, section: str) -> Question:
    assessment = database.get(Assessment, attempt.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    subject = database.scalar(select(Subject).where(
        Subject.exam_id == assessment.exam_id,
        Subject.code == section,
    ))
    if subject is None:
        raise HTTPException(status_code=409, detail=f"The {section} syllabus is not configured for this exam")

    assigned_ids = select(AssessmentQuestionAssignment.question_id).where(
        AssessmentQuestionAssignment.attempt_id == attempt.id,
    )
    question = database.scalar(
        select(Question)
        .join(QuestionAnswer, QuestionAnswer.question_id == Question.id)
        .join(QuestionOption, QuestionOption.question_id == Question.id)
        .where(
            Question.exam_id == assessment.exam_id,
            Question.subject_id == subject.id,
            Question.question_type == QuestionType.MULTIPLE_CHOICE,
            Question.is_published.is_(True),
            QuestionAnswer.correct_option_id.is_not(None),
            ~Question.id.in_(assigned_ids),
        )
        .group_by(Question.id)
        .having(func.count(QuestionOption.id) == 4)
        .order_by(func.random())
        .limit(1)
    )
    return question or random.choice(create_ai_questions(database, assessment.exam_id, subject))


def assign_question(
    database: Session,
    attempt: AssessmentAttempt,
    section: str,
    display_order: int,
) -> AssessmentQuestionAssignment:
    question = choose_mock_question(database, attempt, section)
    assignment = AssessmentQuestionAssignment(
        attempt_id=attempt.id,
        question_id=question.id,
        section_name=section,
        display_order=display_order,
    )
    database.add(assignment)
    database.flush()
    return assignment


def save_answer(
    database: Session,
    attempt: AssessmentAttempt,
    question_id: UUID,
    selected_option_id: UUID | None,
) -> None:
    assignment = database.scalar(select(AssessmentQuestionAssignment).where(
        AssessmentQuestionAssignment.attempt_id == attempt.id,
        AssessmentQuestionAssignment.question_id == question_id,
        AssessmentQuestionAssignment.section_name == attempt.current_round,
    ))
    if assignment is None:
        raise HTTPException(status_code=404, detail="Question is not part of this assessment section")
    if selected_option_id is not None:
        get_question_option(database, question_id, selected_option_id)

    question_attempt = database.scalar(select(QuestionAttempt).where(
        QuestionAttempt.assessment_attempt_id == attempt.id,
        QuestionAttempt.question_id == question_id,
    ))
    if selected_option_id is None:
        if question_attempt is not None:
            database.delete(question_attempt)
        return

    answer = database.scalar(select(QuestionAnswer).where(QuestionAnswer.question_id == question_id))
    if answer is None or answer.correct_option_id is None:
        raise HTTPException(status_code=409, detail="This question does not have a configured correct option")
    is_correct = selected_option_id == answer.correct_option_id
    if question_attempt is None:
        question_attempt = QuestionAttempt(
            user_id=attempt.user_id,
            question_id=question_id,
            assessment_attempt_id=attempt.id,
        )
        database.add(question_attempt)
    question_attempt.selected_option_id = selected_option_id
    question_attempt.is_correct = is_correct
    question_attempt.assessment_round = assignment.section_name


def section_question(
    database: Session,
    attempt: AssessmentAttempt,
    section: str,
    question_number: int,
) -> AssessmentQuestionAssignment:
    assignments = section_assignments(database, attempt, section)
    if question_number <= len(assignments):
        return assignments[question_number - 1]
    if question_number != len(assignments) + 1:
        raise HTTPException(status_code=404, detail="Question is not available yet")
    if question_number > section_question_count(attempt.schedule_type, section):
        raise HTTPException(status_code=422, detail="Question number is outside this section")
    return assign_question(database, attempt, section, question_number)


def complete_attempt(database: Session, attempt: AssessmentAttempt) -> None:
    attempt.status = AttemptStatus.COMPLETED
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.current_question_id = None
    attempt.score = report(database, attempt)["score"]


def move_to_next_section(database: Session, attempt: AssessmentAttempt) -> None:
    if attempt.current_round == "MATH":
        if attempt.schedule_type == "monthly":
            attempt.current_round = "GAT_PENDING"
            attempt.current_question_id = None
            return
        attempt.current_round = "GAT"
        attempt.section_started_at = datetime.now(timezone.utc)
        attempt.current_question_id = assign_question(database, attempt, "GAT", 1).question_id
        return
    complete_attempt(database, attempt)


def expire_section_if_needed(database: Session, attempt: AssessmentAttempt) -> None:
    if (
        attempt.status == AttemptStatus.IN_PROGRESS
        and attempt.current_round in ("MATH", "GAT")
        and section_elapsed_seconds(attempt) >= section_time_limit(attempt.schedule_type)
    ):
        move_to_next_section(database, attempt)
        database.commit()


def question_response(
    database: Session,
    question: Question | None,
    round_name: str,
    question_number: int,
    schedule_type: str,
    selected_option_id: UUID | None = None,
) -> AssessmentQuestionResponse | None:
    if question is None:
        return None
    from app.schemas.assessment import AssessmentOptionResponse
    return AssessmentQuestionResponse(
        id=question.id,
        prompt=question.prompt,
        difficulty=question.difficulty,
        question_type=question.question_type,
        round_name=round_name,
        question_number=question_number,
        total_questions=section_question_count(schedule_type, round_name),
        is_ai_generated=bool(question.tags and "ai-generated" in question.tags.split(",")),
        selected_option_id=selected_option_id,
        options=[AssessmentOptionResponse.model_validate(item, from_attributes=True) for item in options(database, question.id)],
    )


def attempt_response(database: Session, attempt: AssessmentAttempt) -> AssessmentAttemptResponse:
    enforce_same_day(database, attempt)
    expire_section_if_needed(database, attempt)
    question = database.get(Question, attempt.current_question_id) if attempt.current_question_id else None
    assignment = database.scalar(select(AssessmentQuestionAssignment).where(
        AssessmentQuestionAssignment.attempt_id == attempt.id,
        AssessmentQuestionAssignment.question_id == attempt.current_question_id,
    )) if question else None
    question_attempt = database.scalar(select(QuestionAttempt).where(
        QuestionAttempt.assessment_attempt_id == attempt.id,
        QuestionAttempt.question_id == attempt.current_question_id,
    )) if question else None
    total_answered = database.scalar(select(func.count(QuestionAttempt.id)).where(
        QuestionAttempt.assessment_attempt_id == attempt.id,
        QuestionAttempt.selected_option_id.is_not(None),
    )) or 0
    attempt.answered_count = total_answered
    return AssessmentAttemptResponse(
        id=attempt.id,
        status=attempt.status.value,
        current_round=attempt.current_round,
        answered_count=attempt.answered_count,
        schedule_type=attempt.schedule_type,
        section_time_limit_seconds=section_time_limit(attempt.schedule_type),
        section_elapsed_seconds=section_elapsed_seconds(attempt) if attempt.status == AttemptStatus.IN_PROGRESS and attempt.current_round in ("MATH", "GAT") else 0,
        section_completed=attempt.current_round == "GAT_PENDING" or attempt.status == AttemptStatus.COMPLETED,
        same_day_deadline=same_day_deadline(attempt) if attempt.schedule_type == "monthly" else None,
        total_exam_questions=sum(NDA_SECTION_QUESTIONS[attempt.schedule_type].values()),
        score=float(attempt.score) if attempt.score is not None else None,
        question=question_response(
            database,
            question,
            attempt.current_round,
            assignment.display_order if assignment else 1,
            attempt.schedule_type,
            question_attempt.selected_option_id if question_attempt else None,
        ) if question else None,
    )


def owned_attempt(database: Session, user_id: UUID, attempt_id: UUID) -> AssessmentAttempt:
    attempt = database.scalar(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id, AssessmentAttempt.user_id == user_id))
    if attempt is None:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    enforce_same_day(database, attempt)
    return attempt


@router.post("/start", response_model=AssessmentAttemptResponse, status_code=status.HTTP_201_CREATED)
def start_assessment(payload: AssessmentStartRequest, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    from app.models.curriculum import Exam
    if database.get(Exam, payload.exam_id) is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    exam = database.scalar(select(Assessment).where(
        Assessment.exam_id == payload.exam_id,
        Assessment.assessment_type == "nda-mock",
    ))
    if exam is None:
        exam = Assessment(
            exam_id=payload.exam_id,
            title="NDA Mock Examination",
            assessment_type="nda-mock",
            time_limit_seconds=section_time_limit(payload.schedule_type),
        )
        database.add(exam)
        database.flush()
    attempt = AssessmentAttempt(
        assessment_id=exam.id,
        user_id=current_user.id,
        current_round="MATH",
        schedule_type=payload.schedule_type,
        section_started_at=datetime.now(timezone.utc),
    )
    database.add(attempt)
    database.flush()
    attempt.current_question_id = assign_question(database, attempt, "MATH", 1).question_id
    database.commit()
    database.refresh(attempt)
    return attempt_response(database, attempt)


@router.get("/history", response_model=AssessmentHistoryResponse)
def assessment_history(
    exam_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> AssessmentHistoryResponse:
    from app.models.curriculum import Exam

    if database.get(Exam, exam_id) is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    attempts = list(database.scalars(
        select(AssessmentAttempt)
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .where(
            AssessmentAttempt.user_id == current_user.id,
            Assessment.exam_id == exam_id,
            Assessment.assessment_type == "nda-mock",
        )
        .order_by(AssessmentAttempt.started_at.desc())
        .limit(20)
    ))
    completed = [attempt for attempt in attempts if attempt.status == AttemptStatus.COMPLETED and attempt.score is not None]
    scores = [float(attempt.score) for attempt in completed]
    recent_scores = scores[:3]
    previous_scores = scores[3:6]
    average_score = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else None
    previous_average = round(sum(previous_scores) / len(previous_scores), 2) if previous_scores else None
    improvement = round(average_score - previous_average, 2) if average_score is not None and previous_average is not None else None
    now = datetime.now(timezone.utc)

    def due_for(schedule_type: str, interval: timedelta) -> bool:
        latest = next((attempt for attempt in attempts if attempt.schedule_type == schedule_type and attempt.status == AttemptStatus.COMPLETED), None)
        if latest is None:
            return True
        completed_at = latest.completed_at or latest.started_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        return now - completed_at >= interval

    recommendations: list[str] = []
    if average_score is None:
        recommendations.append("Complete your first mock test to establish a performance baseline.")
    elif average_score < 50:
        recommendations.append("Review core concepts and solve topic-wise practice before the next mock.")
    elif average_score < 80:
        recommendations.append("Practice medium-difficulty questions and review every incorrect answer.")
    else:
        recommendations.append("Maintain your accuracy with mixed-difficulty timed practice.")
    if improvement is not None and improvement < 0:
        recommendations.append("Your recent average has dipped; revisit weak topics before increasing difficulty.")
    elif improvement is not None and improvement > 0:
        recommendations.append(f"Your recent average improved by {improvement:g} points. Keep the same study rhythm.")
    if completed:
        latest_recommendations = report(database, completed[0])["recommendations"]
        recommendations.extend(latest_recommendations[:3])

    return AssessmentHistoryResponse(
        exam_id=exam_id,
        total_attempts=len(attempts),
        completed_attempts=len(completed),
        average_score=average_score,
        previous_average_score=previous_average,
        improvement_points=improvement,
        weekly_due=due_for("weekly", timedelta(days=7)),
        monthly_due=due_for("monthly", timedelta(days=30)),
        history=[AssessmentHistoryItem(
            id=attempt.id,
            schedule_type=attempt.schedule_type,
            status=attempt.status.value,
            score=float(attempt.score) if attempt.score is not None else None,
            answered_count=attempt.answered_count,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
        ) for attempt in attempts],
        recommendations=recommendations,
    )


@router.get("/{attempt_id}", response_model=AssessmentAttemptResponse)
def get_assessment(attempt_id: UUID, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    return attempt_response(database, attempt)


@router.post("/{attempt_id}/navigate", response_model=AssessmentAttemptResponse)
def navigate_assessment(attempt_id: UUID, payload: AssessmentNavigateRequest, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS or attempt.current_round not in ("MATH", "GAT"):
        raise HTTPException(status_code=409, detail="This assessment section is not accepting navigation")
    if section_elapsed_seconds(attempt) >= section_time_limit(attempt.schedule_type):
        move_to_next_section(database, attempt)
    else:
        save_answer(database, attempt, payload.current_question_id, payload.selected_option_id)
        if payload.target_question_number > section_question_count(attempt.schedule_type, attempt.current_round):
            raise HTTPException(status_code=422, detail="Question number is outside this section")
        assignment = section_question(database, attempt, attempt.current_round, payload.target_question_number)
        attempt.current_question_id = assignment.question_id
    attempt.answered_count = database.scalar(select(func.count(QuestionAttempt.id)).where(
        QuestionAttempt.assessment_attempt_id == attempt.id,
        QuestionAttempt.selected_option_id.is_not(None),
    )) or 0
    database.commit()
    database.refresh(attempt)
    return attempt_response(database, attempt)


@router.post("/{attempt_id}/finish-section", response_model=AssessmentAttemptResponse)
def finish_assessment_section(attempt_id: UUID, payload: AssessmentSubmitRequest, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS or attempt.current_round != "MATH":
        raise HTTPException(status_code=409, detail="Mathematics section is not awaiting completion")
    section_expired = section_elapsed_seconds(attempt) >= section_time_limit(attempt.schedule_type)
    if not section_expired:
        current_assignment = database.scalar(select(AssessmentQuestionAssignment).where(
            AssessmentQuestionAssignment.attempt_id == attempt.id,
            AssessmentQuestionAssignment.question_id == payload.current_question_id,
            AssessmentQuestionAssignment.section_name == "MATH",
        ))
        if current_assignment is None or current_assignment.display_order != section_question_count(attempt.schedule_type, "MATH"):
            raise HTTPException(status_code=409, detail="Finish Mathematics from its final question")
        save_answer(database, attempt, payload.current_question_id, payload.selected_option_id)
    move_to_next_section(database, attempt)
    attempt.answered_count = database.scalar(select(func.count(QuestionAttempt.id)).where(
        QuestionAttempt.assessment_attempt_id == attempt.id,
        QuestionAttempt.selected_option_id.is_not(None),
    )) or 0
    database.commit()
    database.refresh(attempt)
    return attempt_response(database, attempt)


@router.post("/{attempt_id}/start-gat", response_model=AssessmentAttemptResponse)
def start_gat_section(attempt_id: UUID, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    if attempt.schedule_type != "monthly" or attempt.status != AttemptStatus.IN_PROGRESS or attempt.current_round != "GAT_PENDING":
        raise HTTPException(status_code=409, detail="General Ability section is not ready to start")
    attempt.current_round = "GAT"
    attempt.section_started_at = datetime.now(timezone.utc)
    attempt.current_question_id = assign_question(database, attempt, "GAT", 1).question_id
    database.commit()
    database.refresh(attempt)
    return attempt_response(database, attempt)


@router.post("/{attempt_id}/submit", response_model=AssessmentAttemptResponse)
def submit_assessment(attempt_id: UUID, payload: AssessmentSubmitRequest, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS or attempt.current_round != "GAT":
        raise HTTPException(status_code=409, detail="The General Ability section is not ready to submit")
    section_expired = section_elapsed_seconds(attempt) >= section_time_limit(attempt.schedule_type)
    if not section_expired:
        current_assignment = database.scalar(select(AssessmentQuestionAssignment).where(
            AssessmentQuestionAssignment.attempt_id == attempt.id,
            AssessmentQuestionAssignment.question_id == payload.current_question_id,
            AssessmentQuestionAssignment.section_name == "GAT",
        ))
        if current_assignment is None or current_assignment.display_order != section_question_count(attempt.schedule_type, "GAT"):
            raise HTTPException(status_code=409, detail="Submit the exam from the final GAT question")
        save_answer(database, attempt, payload.current_question_id, payload.selected_option_id)
    complete_attempt(database, attempt)
    attempt.answered_count = database.scalar(select(func.count(QuestionAttempt.id)).where(
        QuestionAttempt.assessment_attempt_id == attempt.id,
        QuestionAttempt.selected_option_id.is_not(None),
    )) or 0
    database.commit()
    database.refresh(attempt)
    return attempt_response(database, attempt)


@router.post("/{attempt_id}/abandon", response_model=AssessmentAttemptResponse)
def abandon_assessment(attempt_id: UUID, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentAttemptResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="This assessment is not in progress")
    attempt.status = AttemptStatus.ABANDONED
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.current_question_id = None
    database.commit()
    database.refresh(attempt)
    return attempt_response(database, attempt)


@router.get("/{attempt_id}/report", response_model=AssessmentReportResponse)
def get_report(attempt_id: UUID, current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> AssessmentReportResponse:
    attempt = owned_attempt(database, current_user.id, attempt_id)
    if attempt.status != AttemptStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="A report is available only for completed assessments")
    return AssessmentReportResponse.model_validate(report(database, attempt))
