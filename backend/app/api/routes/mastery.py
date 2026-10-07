"""Student mastery evidence endpoints for Phase 10."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.curriculum import Concept
from app.models.users import User
from app.schemas.mastery import MasterySummaryResponse
from app.services.mastery_engine import mastery_summary


router = APIRouter(prefix="/mastery", tags=["Mastery"])


@router.get("/concepts/{concept_id}", response_model=MasterySummaryResponse)
def get_concept_mastery(
    concept_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> MasterySummaryResponse:
    if database.get(Concept, concept_id) is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return MasterySummaryResponse.model_validate(mastery_summary(database, current_user.id, concept_id))