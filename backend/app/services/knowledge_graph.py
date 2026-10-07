"""Deterministic prerequisite graph traversal for Phase 5."""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.curriculum import Concept, Prerequisite


class KnowledgeGraphCycleError(ValueError):
    """Raised when prerequisite data contains a cycle."""


def build_learning_path(database: Session, target_concept_id: UUID) -> list[Concept]:
    """Return required concepts in prerequisite-first order, ending at the target."""
    concepts = {concept.id: concept for concept in database.scalars(select(Concept)).all()}
    if target_concept_id not in concepts:
        raise KeyError(target_concept_id)

    prerequisites: dict[UUID, list[UUID]] = defaultdict(list)
    edges = database.scalars(
        select(Prerequisite).where(Prerequisite.is_required.is_(True))
    ).all()
    for edge in edges:
        prerequisites[edge.concept_id].append(edge.prerequisite_concept_id)

    for concept_id in prerequisites:
        prerequisites[concept_id].sort(key=lambda item: str(item))

    ordered_ids: list[UUID] = []
    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(concept_id: UUID) -> None:
        if concept_id in visiting:
            raise KnowledgeGraphCycleError("Prerequisite cycle detected")
        if concept_id in visited:
            return
        if concept_id not in concepts:
            raise ValueError(f"Prerequisite references missing concept {concept_id}")
        visiting.add(concept_id)
        for prerequisite_id in prerequisites.get(concept_id, []):
            visit(prerequisite_id)
        visiting.remove(concept_id)
        visited.add(concept_id)
        ordered_ids.append(concept_id)

    visit(target_concept_id)
    return [concepts[concept_id] for concept_id in ordered_ids]
