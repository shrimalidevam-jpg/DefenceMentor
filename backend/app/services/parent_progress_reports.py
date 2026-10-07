"""Scheduled WhatsApp progress reports for opted-in student guardians."""

import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.assessment import AssessmentAttempt
from app.models.enums import AttemptStatus
from app.models.learning import StudentMastery
from app.models.parent_progress_report import ParentProgressReport
from app.models.study_planner import StudyPlanTask
from app.models.users import StudentProfile, User


logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


class ParentReportProviderError(RuntimeError):
    """Raised when WhatsApp Cloud API cannot accept a report message."""


def _report_window(period: str, today: date) -> tuple[date, date]:
    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == "monthly":
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, next_month - timedelta(days=1)
    raise ValueError(f"Unsupported report period: {period}")


def _send_whatsapp_template(phone: str, student_name: str, period: str, summary: str) -> str:
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        raise ParentReportProviderError("WhatsApp Cloud API credentials are not configured")
    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone.lstrip("+"),
                "type": "template",
                "template": {
                    "name": settings.WHATSAPP_TEMPLATE_NAME,
                    "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
                    "components": [{
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": student_name[:100]},
                            {"type": "text", "text": period.capitalize()},
                            {"type": "text", "text": summary[:900]},
                        ],
                    }],
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        message_id = response.json()["messages"][0]["id"]
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
        raise ParentReportProviderError("WhatsApp Cloud API did not accept the progress report") from error
    if not isinstance(message_id, str) or not message_id:
        raise ParentReportProviderError("WhatsApp Cloud API returned no message identifier")
    return message_id


def _build_summary(database: Session, user_id: object, start: date, end: date) -> str:
    planned, completed = database.execute(
        select(
            func.count(StudyPlanTask.id),
            func.coalesce(func.sum(case((StudyPlanTask.is_completed.is_(True), 1), else_=0)), 0),
        ).where(
            StudyPlanTask.user_id == user_id,
            StudyPlanTask.plan_date >= start,
            StudyPlanTask.plan_date <= end,
        )
    ).one()
    attempts = list(database.scalars(
        select(AssessmentAttempt).where(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.started_at >= datetime.combine(start, time.min, tzinfo=ZoneInfo(settings.APP_TIMEZONE)),
            AssessmentAttempt.started_at < datetime.combine(end + timedelta(days=1), time.min, tzinfo=ZoneInfo(settings.APP_TIMEZONE)),
            AssessmentAttempt.status == AttemptStatus.COMPLETED,
        )
    ))
    scored_attempts = [attempt.score for attempt in attempts if attempt.score is not None]
    mastery_count = database.scalar(
        select(func.count(StudentMastery.id)).where(
            StudentMastery.user_id == user_id,
            StudentMastery.score >= settings.MASTERY_THRESHOLD,
        )
    ) or 0
    average_score = sum(scored_attempts) / len(scored_attempts) if scored_attempts else None
    score_text = f"{average_score:.1f}%" if average_score is not None else "no scored mock yet"
    return (
        f"{start:%d %b}-{end:%d %b %Y}: study tasks completed {int(completed)}/{planned}; "
        f"completed mock tests {len(attempts)} (average score {score_text}); "
        f"topics at mastery level {mastery_count}. Keep encouraging steady NDA preparation."
    )


def send_parent_reports(period: str, today: date | None = None) -> None:
    """Send one scheduled report to each consenting guardian, recording successful sends."""
    local_today = today or datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()
    start, end = _report_window(period, local_today)
    database = SessionLocal()
    try:
        recipients = list(database.execute(
            select(StudentProfile, User)
            .join(User, User.id == StudentProfile.user_id)
            .where(
                StudentProfile.guardian_report_consent_at.is_not(None),
                StudentProfile.parent_phone.is_not(None),
            )
        ))
        for profile, user in recipients:
            previous = database.scalar(select(ParentProgressReport.id).where(
                ParentProgressReport.user_id == user.id,
                ParentProgressReport.period == period,
                ParentProgressReport.period_start == start,
                ParentProgressReport.sent_at.is_not(None),
            ))
            if previous:
                continue
            summary = _build_summary(database, user.id, start, end)
            try:
                message_id = _send_whatsapp_template(profile.parent_phone, user.full_name, period, summary)
            except ParentReportProviderError:
                logger.exception("Unable to send %s parent report for student %s", period, user.id)
                continue
            database.add(ParentProgressReport(
                user_id=user.id,
                period=period,
                period_start=start,
                period_end=end,
                sent_at=datetime.now(ZoneInfo(settings.APP_TIMEZONE)),
                provider_message_id=message_id,
            ))
            database.commit()
    finally:
        database.close()


def start_parent_report_scheduler() -> None:
    """Start the single-process development scheduler; reports require WhatsApp credentials."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    try:
        timezone = ZoneInfo(settings.APP_TIMEZONE)
    except ZoneInfoNotFoundError as error:
        raise RuntimeError(f"Invalid APP_TIMEZONE: {settings.APP_TIMEZONE}") from error
    scheduler = BackgroundScheduler(timezone=timezone)
    scheduler.add_job(
        send_parent_reports,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=timezone),
        args=["weekly"],
        id="weekly-parent-progress-reports",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        send_parent_reports,
        CronTrigger(day="last", hour=18, minute=0, timezone=timezone),
        args=["monthly"],
        id="monthly-parent-progress-reports",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler


def stop_parent_report_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
