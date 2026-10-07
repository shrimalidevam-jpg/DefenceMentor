"""Deterministic adaptive examination engine for Phase 11."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment, AssessmentAttempt
from app.models.enums import AttemptStatus, Difficulty
from app.models.curriculum import Subject, Topic
from app.models.questions import Question, QuestionAnswer, QuestionAttempt, QuestionOption


ROUNDS = ("easy", "medium", "hard", "general")
NDA_SECTION_QUESTIONS = {
    "weekly": {"MATH": 25, "GAT": 25},
    "monthly": {"MATH": 120, "GAT": 150},
}
NDA_SECTION_TIME_SECONDS = {"weekly": 15 * 60, "monthly": 2 * 60 * 60 + 30 * 60}
NDA_MARKS_PER_QUESTION = {"MATH": 2.5, "GAT": 4.0}


def difficulty_for_performance(accuracy: float) -> str:
    if accuracy >= settings.ADAPTIVE_HIGH_THRESHOLD:
        return Difficulty.HARD.value
    if accuracy >= settings.ADAPTIVE_MEDIUM_THRESHOLD:
        return Difficulty.MEDIUM.value
    return Difficulty.EASY.value


def round_difficulty(round_name: str, previous_accuracy: float | None) -> list[str]:
    if round_name == "general":
        if previous_accuracy is None:
            return [Difficulty.EASY.value]
        return [difficulty_for_performance(previous_accuracy)]
    if previous_accuracy is None:
        return [round_name]
    return [difficulty_for_performance(previous_accuracy)]


def answered_question_ids(database: Session, attempt_id: UUID) -> select:
    return select(QuestionAttempt.question_id).where(QuestionAttempt.assessment_attempt_id == attempt_id)


def round_accuracy(database: Session, attempt_id: UUID, round_name: str) -> float:
    total = database.scalar(select(func.count(QuestionAttempt.id)).where(QuestionAttempt.assessment_attempt_id == attempt_id, QuestionAttempt.assessment_round == round_name)) or 0
    correct = database.scalar(select(func.count(QuestionAttempt.id)).where(QuestionAttempt.assessment_attempt_id == attempt_id, QuestionAttempt.assessment_round == round_name, QuestionAttempt.is_correct.is_(True))) or 0
    return round((correct / total) * 100, 2) if total else 0.0


def choose_question(database: Session, attempt: AssessmentAttempt, previous_accuracy: float | None = None) -> Question | None:
    if attempt.current_round == "general":
        answered_in_round = database.scalar(
            select(func.count(QuestionAttempt.id)).where(
                QuestionAttempt.assessment_attempt_id == attempt.id,
                QuestionAttempt.assessment_round == attempt.current_round,
            )
        ) or 0
        if answered_in_round:
            previous_accuracy = round_accuracy(database, attempt.id, attempt.current_round) / 100
    difficulties = round_difficulty(attempt.current_round, previous_accuracy)
    query = select(Question).where(
        Question.exam_id == database.scalar(select(Assessment.exam_id).where(Assessment.id == attempt.assessment_id)),
        Question.is_published.is_(True),
        Question.difficulty.in_(difficulties),
        ~Question.id.in_(answered_question_ids(database, attempt.id)),
    )
    question = database.scalar(query.order_by(Question.created_at))
    if question is not None or attempt.current_round != "general":
        return question
    return database.scalar(
        select(Question).where(
            Question.exam_id == database.scalar(select(Assessment.exam_id).where(Assessment.id == attempt.assessment_id)),
            Question.is_published.is_(True),
            ~Question.id.in_(answered_question_ids(database, attempt.id)),
        ).order_by(Question.created_at)
    )


def options(database: Session, question_id: UUID) -> list[QuestionOption]:
    return list(database.scalars(select(QuestionOption).where(QuestionOption.question_id == question_id).order_by(QuestionOption.display_order)))


def advance_round(attempt: AssessmentAttempt, accuracy: float) -> None:
    current_index = ROUNDS.index(attempt.current_round)
    if current_index >= len(ROUNDS) - 1:
        return
    attempt.current_round = ROUNDS[current_index + 1]


def report(database: Session, attempt: AssessmentAttempt) -> dict:
    attempts = list(
        database.execute(
            select(QuestionAttempt, Question)
            .join(Question, Question.id == QuestionAttempt.question_id)
            .where(QuestionAttempt.assessment_attempt_id == attempt.id)
        ).all()
    )
    subjects = dict(database.execute(select(Subject.id, Subject.name)).all())
    subject_codes = dict(database.execute(select(Subject.id, Subject.code)).all())
    topics = dict(database.execute(select(Topic.id, Topic.name)).all())
    question_attempts = [item[0] for item in attempts]
    correct = sum(1 for item in question_attempts if item.is_correct)
    expected_questions = NDA_SECTION_QUESTIONS.get(attempt.schedule_type)
    total = sum(expected_questions.values()) if expected_questions else len(question_attempts)
    net_marks = 0.0
    maximum_marks = 0.0
    for section, question_count in (expected_questions or {}).items():
        marks = NDA_MARKS_PER_QUESTION[section]
        section_attempts = [item for item, question in attempts if subject_codes.get(question.subject_id) == section]
        section_correct = sum(1 for item in section_attempts if item.is_correct)
        section_wrong = sum(1 for item in section_attempts if not item.is_correct)
        net_marks += section_correct * marks - section_wrong * marks / 3
        maximum_marks += question_count * marks

    def performance(key_function) -> dict[str, dict[str, float]]:
        grouped: dict[str, list[QuestionAttempt]] = {}
        for question_attempt, question in attempts:
            key = key_function(question_attempt, question)
            grouped.setdefault(key, []).append(question_attempt)
        return {
            key: {
                "correct_answers": float(sum(1 for item in items if item.is_correct)),
                "total_questions": float(len(items)),
                "accuracy": round(sum(1 for item in items if item.is_correct) / len(items) * 100, 2),
            }
            for key, items in grouped.items()
        }

    average_response_time = round(
        sum(item.response_time_seconds for item in question_attempts if item.response_time_seconds is not None)
        / max(1, sum(1 for item in question_attempts if item.response_time_seconds is not None)),
        2,
    )
    recommendations = [
        f"Revise {name}" for name, values in performance(lambda _attempt, question: subjects.get(question.subject_id, "Unknown subject")).items() if values["accuracy"] < 50
    ]
    recommendations.extend(
        f"Practice {name}" for name, values in performance(lambda _attempt, question: topics.get(question.topic_id, "General")) .items() if values["accuracy"] < 50
    )
    section_performance: dict[str, float] = {}
    for section in ("MATH", "GAT"):
        section_attempts = [
            item for item in question_attempts if item.assessment_round == section
        ]
        section_performance[section] = round(
            sum(1 for item in section_attempts if item.is_correct)
            / len(section_attempts)
            * 100,
            2,
        ) if section_attempts else 0.0

    return {
        "attempt_id": attempt.id,
        "status": attempt.status.value,
        "score": round((net_marks / maximum_marks) * 100, 2) if maximum_marks else 0.0,
        "total_questions": total,
        "correct_answers": correct,
        "accuracy": round((correct / total) * 100, 2) if total else 0.0,
        "round_performance": section_performance,
        "difficulty_performance": performance(lambda _attempt, question: question.difficulty.value),
        "subject_performance": performance(lambda _attempt, question: subjects.get(question.subject_id, "Unknown subject")),
        "topic_performance": performance(lambda _attempt, question: topics.get(question.topic_id, "General")),
        "average_response_time_seconds": average_response_time,
        "net_marks": round(net_marks, 2),
        "maximum_marks": maximum_marks,
        "recommendations": recommendations,
    }


def evaluate_exam_answer(database: Session, attempt: AssessmentAttempt, question: Question, selected_option_id: UUID | None, answer_text: str | None, response_time_seconds: int | None, confidence: float | None) -> tuple[bool, dict]:
    answer = database.scalar(select(QuestionAnswer).where(QuestionAnswer.question_id == question.id))
    if answer is None:
        raise ValueError("This question does not have a configured answer")
    is_correct = (selected_option_id is not None and selected_option_id == answer.correct_option_id) or (answer_text is not None and answer.correct_text is not None and answer_text.strip().casefold() == answer.correct_text.strip().casefold())
    database.add(QuestionAttempt(user_id=attempt.user_id, question_id=question.id, selected_option_id=selected_option_id, answer_text=answer_text.strip() if answer_text else None, is_correct=is_correct, response_time_seconds=response_time_seconds, confidence=confidence, assessment_attempt_id=attempt.id, assessment_round=attempt.current_round))
    database.flush()
    attempt.answered_count += 1
    round_count = database.scalar(select(func.count(QuestionAttempt.id)).where(QuestionAttempt.assessment_attempt_id == attempt.id, QuestionAttempt.assessment_round == attempt.current_round)) or 0
    previous_accuracy: float | None = None
    if round_count >= settings.ADAPTIVE_QUESTIONS_PER_ROUND:
        accuracy = round_accuracy(database, attempt.id, attempt.current_round)
        previous_accuracy = accuracy / 100
        advance_round(attempt, accuracy)
    database.flush()
    next_question = choose_question(database, attempt, previous_accuracy)
    if next_question is None:
        attempt.status = AttemptStatus.COMPLETED
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.score = report(database, attempt)["score"]
        attempt.current_question_id = None
    else:
        attempt.current_question_id = next_question.id
    database.commit()
    return is_correct, {"explanation": question.explanation, "next_question": next_question}
