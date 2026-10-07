"""Student browsing and administrator management for verified tutorials."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models.tutorials import TutorialResource
from app.models.users import User
from app.schemas.tutorials import TutorialPublishRequest, TutorialResourceCreate, TutorialResourceResponse


router = APIRouter(prefix="/tutorials", tags=["Tutorials"])
admin_router = APIRouter(prefix="/admin/tutorials", tags=["Tutorial administration"])


@router.get("", response_model=list[TutorialResourceResponse])
def list_tutorials(
    board: str | None = Query(default=None),
    grade_level: int | None = Query(default=None, ge=5, le=12),
    subject: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    database: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[TutorialResource]:
    statement = select(TutorialResource).where(
        TutorialResource.is_verified.is_(True),
        TutorialResource.is_published.is_(True),
    )
    if board:
        statement = statement.where(TutorialResource.board == board)
    if grade_level:
        statement = statement.where(TutorialResource.grade_level == grade_level)
    if subject:
        statement = statement.where(TutorialResource.subject == subject)
    if topic:
        statement = statement.where(TutorialResource.topic == topic)
    return list(database.scalars(statement.order_by(TutorialResource.grade_level, TutorialResource.subject, TutorialResource.topic, TutorialResource.title)))


@admin_router.post("", response_model=TutorialResourceResponse, status_code=status.HTTP_201_CREATED)
def create_tutorial(
    payload: TutorialResourceCreate,
    database: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> TutorialResource:
    values = payload.model_dump(mode="json")
    values["url"] = str(payload.url)
    resource = TutorialResource(**values, verified_by=admin_user.id)
    database.add(resource)
    database.commit()
    database.refresh(resource)
    return resource


@admin_router.patch("/{resource_id}/publication", response_model=TutorialResourceResponse)
def publish_tutorial(
    resource_id: UUID,
    payload: TutorialPublishRequest,
    database: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> TutorialResource:
    resource = database.get(TutorialResource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Tutorial resource not found")
    resource.is_verified = payload.is_verified
    resource.is_published = payload.is_published and payload.is_verified
    resource.verified_at = datetime.now(timezone.utc) if payload.is_verified else None
    resource.verified_by = admin_user.id if payload.is_verified else None
    database.commit()
    database.refresh(resource)
    return resource
