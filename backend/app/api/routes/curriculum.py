"""Read endpoints for the Phase 4 NDA curriculum hierarchy."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.curriculum import Chapter, Concept, Exam, Prerequisite, Subject, Topic
from app.services.knowledge_graph import KnowledgeGraphCycleError, build_learning_path
from app.schemas.curriculum import (
    ChapterResponse,
    ConceptResponse,
    ExamResponse,
    LearningPathItem,
    PrerequisiteResponse,
    SubjectResponse,
    TopicResponse,
)


router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


def get_or_404(database: Session, model: type, item_id: UUID, label: str):
    item = database.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return item


@router.get("/exams", response_model=list[ExamResponse])
def list_exams(database: Session = Depends(get_db)) -> list[Exam]:
    return list(database.scalars(select(Exam).where(Exam.is_active.is_(True)).order_by(Exam.name)))


@router.get("/exams/{exam_id}/subjects", response_model=list[SubjectResponse])
def list_subjects(exam_id: UUID, database: Session = Depends(get_db)) -> list[Subject]:
    get_or_404(database, Exam, exam_id, "Exam")
    return list(database.scalars(select(Subject).where(Subject.exam_id == exam_id).order_by(Subject.display_order, Subject.name)))


@router.get("/subjects/{subject_id}/chapters", response_model=list[ChapterResponse])
def list_chapters(subject_id: UUID, database: Session = Depends(get_db)) -> list[Chapter]:
    get_or_404(database, Subject, subject_id, "Subject")
    return list(database.scalars(select(Chapter).where(Chapter.subject_id == subject_id).order_by(Chapter.display_order, Chapter.name)))


@router.get("/chapters/{chapter_id}/topics", response_model=list[TopicResponse])
def list_topics(chapter_id: UUID, database: Session = Depends(get_db)) -> list[Topic]:
    get_or_404(database, Chapter, chapter_id, "Chapter")
    return list(database.scalars(select(Topic).where(Topic.chapter_id == chapter_id).order_by(Topic.display_order, Topic.name)))


@router.get("/topics/{topic_id}/concepts", response_model=list[ConceptResponse])
def list_concepts(topic_id: UUID, database: Session = Depends(get_db)) -> list[Concept]:
    get_or_404(database, Topic, topic_id, "Topic")
    return list(database.scalars(select(Concept).where(Concept.topic_id == topic_id).order_by(Concept.display_order, Concept.name)))


@router.get("/concepts/{concept_id}/prerequisites", response_model=list[PrerequisiteResponse])
def list_prerequisites(concept_id: UUID, database: Session = Depends(get_db)) -> list[Prerequisite]:
    get_or_404(database, Concept, concept_id, "Concept")
    return list(database.scalars(select(Prerequisite).where(Prerequisite.concept_id == concept_id)))


@router.get("/concepts/{concept_id}/learning-path", response_model=list[LearningPathItem])
def get_learning_path(concept_id: UUID, database: Session = Depends(get_db)) -> list[LearningPathItem]:
    get_or_404(database, Concept, concept_id, "Concept")
    try:
        concepts = build_learning_path(database, concept_id)
    except KnowledgeGraphCycleError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return [
        LearningPathItem(order=index, concept=concept, is_target=concept.id == concept_id)
        for index, concept in enumerate(concepts, start=1)
    ]
