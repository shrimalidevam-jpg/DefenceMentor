"""Personalized daily SSB guidance and an SSB-specific coaching chat."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.clock import india_today
from app.core.database import get_db
from app.models.ssb_guidance import DailySSBGuidance, SSBGuidanceMessage
from app.models.users import User
from app.schemas.ssb_guidance import (
    DailySSBGuidanceResponse,
    SSBGuidanceChatResponse,
    SSBGuidanceMessageCreate,
    SSBGuidanceMessageResponse,
)
from app.services.ai_provider import AIProviderError, get_ai_provider


router = APIRouter(prefix="/ssb-guidance", tags=["SSB guidance"])

SSB_OLQS = (
    "Effective Intelligence",
    "Reasoning Ability",
    "Organising Ability",
    "Power of Expression",
    "Social Adaptability",
    "Cooperation",
    "Sense of Responsibility",
    "Initiative",
    "Self-Confidence",
    "Speed of Decision",
    "Ability to Influence the Group",
    "Liveliness",
    "Determination",
    "Courage",
    "Stamina",
)


def _decode_daily_guidance(content: str) -> dict[str, str]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise AIProviderError("The AI provider returned invalid daily SSB guidance data") from error
    if not isinstance(payload, dict):
        raise AIProviderError("The AI provider returned invalid daily SSB guidance data")
    fields = ("title", "guidance", "action", "reflection_question")
    if any(not isinstance(payload.get(field), str) or not payload[field].strip() for field in fields):
        raise AIProviderError("The AI provider returned incomplete daily SSB guidance")
    normalized = {field: payload[field].strip() for field in fields}
    if len(normalized["title"]) > 160 or any(
        len(normalized[field]) > 1200 for field in fields[1:]
    ):
        raise AIProviderError("The AI provider returned daily SSB guidance that is too long")
    return normalized


def _daily_response(item: DailySSBGuidance) -> DailySSBGuidanceResponse:
    return DailySSBGuidanceResponse(
        guidance_date=item.guidance_date,
        title=item.title,
        guidance=item.guidance,
        action=item.action,
        reflection_question=item.reflection_question,
    )


def _get_or_create_daily_guidance(database: Session, user: User) -> DailySSBGuidance:
    today = india_today()
    existing = database.scalar(
        select(DailySSBGuidance).where(
            DailySSBGuidance.user_id == user.id,
            DailySSBGuidance.guidance_date == today,
        )
    )
    if existing is not None:
        return existing

    try:
        raw = get_ai_provider().generate([
            {
                "role": "system",
                "content": (
                    "You are a supportive, practical NDA Services Selection Board (SSB) preparation coach. "
                    "Create exactly one concise daily coaching card about an Officer Like Quality (OLQ), "
                    "communication, self-awareness, teamwork, responsibility, or interview/group-task preparation. "
                    "Make it honest and actionable; do not promise selection, diagnose the student, or encourage "
                    "memorised/fabricated interview answers. Return only JSON with non-empty string keys "
                    "title, guidance, action, reflection_question."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Student: {user.full_name}. Date in India: {today.isoformat()}. "
                    f"Today's 15 OLQs: {', '.join(SSB_OLQS)}. "
                    "Give one fresh daily suggestion and a small real-life practice action."
                ),
            },
        ])
        content = _decode_daily_guidance(raw)
    except AIProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Today's SSB guidance could not be generated: {error}",
        ) from error

    item = DailySSBGuidance(
        user_id=user.id,
        guidance_date=today,
        **content,
    )
    database.add(item)
    try:
        database.commit()
        database.refresh(item)
        return item
    except IntegrityError:
        database.rollback()
        existing = database.scalar(
            select(DailySSBGuidance).where(
                DailySSBGuidance.user_id == user.id,
                DailySSBGuidance.guidance_date == today,
            )
        )
        if existing is None:
            raise
        return existing


@router.get("/today", response_model=DailySSBGuidanceResponse)
def get_today_guidance(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> DailySSBGuidanceResponse:
    return _daily_response(_get_or_create_daily_guidance(database, current_user))


@router.get("/chat", response_model=SSBGuidanceChatResponse)
def get_ssb_chat(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> SSBGuidanceChatResponse:
    messages = list(database.scalars(
        select(SSBGuidanceMessage)
        .where(SSBGuidanceMessage.user_id == current_user.id)
        .order_by(SSBGuidanceMessage.created_at.desc(), SSBGuidanceMessage.id.desc())
        .limit(100)
    ))
    messages.reverse()
    return SSBGuidanceChatResponse(
        messages=[SSBGuidanceMessageResponse.model_validate(item) for item in messages]
    )


@router.post("/chat", response_model=list[SSBGuidanceMessageResponse], status_code=status.HTTP_201_CREATED)
def send_ssb_chat_message(
    payload: SSBGuidanceMessageCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> list[SSBGuidanceMessageResponse]:
    content = payload.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    history = list(database.scalars(
        select(SSBGuidanceMessage)
        .where(SSBGuidanceMessage.user_id == current_user.id)
        .order_by(SSBGuidanceMessage.created_at.desc(), SSBGuidanceMessage.id.desc())
        .limit(12)
    ))
    history.reverse()
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are the student's dedicated NDA SSB and personality-development coach. "
                "Answer questions about SSB stages, interview preparation, communication, group tasks, "
                "self-awareness, confidence, teamwork and building Officer Like Qualities through genuine "
                "daily behaviour. Give supportive, specific, practical suggestions and ask at most one useful "
                "follow-up question. Never promise selection, invent official procedures or current facts, "
                "encourage deception/memorised false answers, or shame the student. If a fact may have changed, "
                "say it should be checked against the latest official UPSC/SSB instructions. This is coaching, "
                "not a psychological diagnosis. Be concise and match the student's language."
            ),
        },
        *({"role": item.role, "content": item.content} for item in history),
        {"role": "user", "content": content},
    ]
    try:
        answer = get_ai_provider().generate(messages).strip()
    except AIProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SSB chat could not get an AI response: {error}",
        ) from error
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSB chat received an empty AI response.",
        )

    now = datetime.now(timezone.utc)
    assistant_time = now + timedelta(microseconds=1)
    user_message = SSBGuidanceMessage(user_id=current_user.id, role="user", content=content, created_at=now, updated_at=now)
    assistant_message = SSBGuidanceMessage(user_id=current_user.id, role="assistant", content=answer, created_at=assistant_time, updated_at=assistant_time)
    database.add_all([user_message, assistant_message])
    database.commit()
    database.refresh(user_message)
    database.refresh(assistant_message)
    return [
        SSBGuidanceMessageResponse.model_validate(user_message),
        SSBGuidanceMessageResponse.model_validate(assistant_message),
    ]
