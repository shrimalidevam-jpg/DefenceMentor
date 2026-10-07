"""Google authentication, profile and admin authorization routes."""

import base64
from io import BytesIO
from datetime import date
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from fastapi import APIRouter, Depends, HTTPException, Response, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, inspect as sqlalchemy_inspect, select, text, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.users import StudentProfile, User
from app.models.assessment import AssessmentAttempt, AssessmentQuestionAssignment
from app.models.chat import ChatMessage, ChatSession
from app.models.daily_review import DailyReviewAttempt, DailyReviewItem
from app.models.daily_vocabulary import DailyVocabularyAttempt
from app.models.learning import LearningProgress, LearningSession, StudentMastery
from app.models.notifications import AdminUser, Notification
from app.models.parent_progress_report import ParentProgressReport
from app.models.questions import QuestionAttempt
from app.models.study_planner import StudyPlanTask
from app.models.tutorials import TutorialResource
from app.schemas.auth import (
    AccessTokenResponse,
    GoogleLoginRequest,
    LoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _normalize_profile_photo(data_url: str) -> bytes:
    encoded = data_url.partition(",")[2]
    raw = base64.b64decode(encoded, validate=True)
    try:
        with Image.open(BytesIO(raw)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 16_000_000:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded photo must be a supported image under 16 megapixels")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1280, 1280))
            output = BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded photo is not a valid image") from error


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, database: Session = Depends(get_db)) -> User:
    normalized_email = str(payload.email).lower()
    existing_user = database.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(email=normalized_email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    database.add(user)
    database.flush()
    database.add(StudentProfile(
        user_id=user.id,
        exam_target=payload.exam_target,
        current_level=payload.current_level,
        academic_stream=payload.academic_stream,
        science_group=payload.science_group,
        student_phone=payload.student_phone,
        parent_phone=payload.parent_phone,
        student_photo=_normalize_profile_photo(payload.student_photo_data),
        parent_photo=_normalize_profile_photo(payload.parent_photo_data),
        guardian_report_consent_at=date.today(),
    ))
    database.commit()
    database.refresh(user)
    return user


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: LoginRequest, database: Session = Depends(get_db)) -> AccessTokenResponse:
    user = database.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return AccessTokenResponse(access_token=create_access_token(str(user.id), user.role.value))


@router.post("/google", response_model=AccessTokenResponse)
def google_login(payload: GoogleLoginRequest, database: Session = Depends(get_db)) -> AccessTokenResponse:
    """Verify a Google Identity Services credential for a registered student."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google sign-in is not configured")
    try:
        claims = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except (GoogleAuthError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential") from error

    email = claims.get("email")
    if not isinstance(email, str) or not claims.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A verified Google email is required")

    normalized_email = email.lower()
    user = database.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create your account using the registration form so parent contact and consent details can be collected.",
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account is inactive")

    return AccessTokenResponse(access_token=create_access_token(str(user.id), user.role.value))


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_account(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> Response:
    """Permanently delete the signed-in account and its personal learning data."""
    user_id = current_user.id
    # Delete child records explicitly so this also works on SQLite databases where
    # foreign-key cascades may not be enabled on the connection.
    database.execute(delete(ChatMessage).where(ChatMessage.chat_session_id.in_(
        select(ChatSession.id).where(ChatSession.user_id == user_id)
    )))
    database.execute(delete(DailyReviewItem).where(DailyReviewItem.attempt_id.in_(
        select(DailyReviewAttempt.id).where(DailyReviewAttempt.user_id == user_id)
    )))
    schema = sqlalchemy_inspect(database.get_bind())
    learning_progress_columns = {column["name"] for column in schema.get_columns(LearningProgress.__tablename__)}
    progress_session_column = next((name for name in ("session_id", "learning_session_id") if name in learning_progress_columns), None)
    if progress_session_column:
        database.execute(text(
            f"DELETE FROM learning_progress WHERE {progress_session_column} IN "
            "(SELECT id FROM learning_sessions WHERE user_id = :user_id)"
        ), {"user_id": user_id})
    database.execute(delete(AssessmentQuestionAssignment).where(AssessmentQuestionAssignment.attempt_id.in_(
        select(AssessmentAttempt.id).where(AssessmentAttempt.user_id == user_id)
    )))
    database.execute(delete(QuestionAttempt).where(QuestionAttempt.user_id == user_id))

    database.execute(delete(ChatSession).where(ChatSession.user_id == user_id))
    database.execute(delete(DailyReviewAttempt).where(DailyReviewAttempt.user_id == user_id))
    database.execute(delete(LearningSession).where(LearningSession.user_id == user_id))
    database.execute(delete(AssessmentAttempt).where(AssessmentAttempt.user_id == user_id))
    # Older databases stored student-owned assessment rows and question links.
    assessment_columns = {column["name"] for column in schema.get_columns("assessments")}
    table_names = set(schema.get_table_names())
    if "user_id" in assessment_columns:
        if "assessment_questions" in table_names:
            database.execute(text(
                "DELETE FROM assessment_questions WHERE assessment_id IN "
                "(SELECT id FROM assessments WHERE user_id = :user_id)"
            ), {"user_id": user_id})
        database.execute(text("DELETE FROM assessments WHERE user_id = :user_id"), {"user_id": user_id})
    database.execute(delete(StudyPlanTask).where(StudyPlanTask.user_id == user_id))
    database.execute(delete(DailyVocabularyAttempt).where(DailyVocabularyAttempt.user_id == user_id))
    database.execute(delete(StudentMastery).where(StudentMastery.user_id == user_id))
    database.execute(delete(Notification).where(Notification.user_id == user_id))
    database.execute(delete(ParentProgressReport).where(ParentProgressReport.user_id == user_id))
    database.execute(delete(AdminUser).where(AdminUser.user_id == user_id))
    database.execute(delete(StudentProfile).where(StudentProfile.user_id == user_id))
    database.execute(update(TutorialResource).where(TutorialResource.verified_by == user_id).values(verified_by=None))
    database.execute(delete(User).where(User.id == user_id).execution_options(synchronize_session=False))
    database.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/profile", response_model=ProfileResponse)
def read_profile(current_user: User = Depends(get_current_user), database: Session = Depends(get_db)) -> StudentProfile:
    profile = database.scalar(select(StudentProfile).where(StudentProfile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return profile


@router.patch("/me/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> StudentProfile:
    profile = database.scalar(select(StudentProfile).where(StudentProfile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    updates = payload.model_dump(exclude_unset=True)
    report_consent = updates.pop("guardian_report_consent", None)
    for field_name, value in updates.items():
        setattr(profile, field_name, value)
    if report_consent is False:
        profile.guardian_report_consent_at = None
    elif report_consent is True:
        if not profile.parent_phone:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Add a parent WhatsApp number before enabling progress reports")
        profile.guardian_report_consent_at = date.today()
    database.commit()
    database.refresh(profile)
    return profile


@router.get("/admin/me", response_model=UserResponse, tags=["Administration"])
def read_admin_identity(admin_user: User = Depends(require_admin)) -> User:
    return admin_user
