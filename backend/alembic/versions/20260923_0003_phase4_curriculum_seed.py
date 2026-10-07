"""Seed the Phase 4 NDA curriculum hierarchy without duplicating existing rows."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op


revision = "20260923_0003"
down_revision = "20260923_0002"
branch_labels = None
depends_on = None

SEED_IDS = {
    "exam": UUID("00000000-0000-0000-0000-000000000001"),
    "math": UUID("00000000-0000-0000-0000-000000000011"),
    "gat": UUID("00000000-0000-0000-0000-000000000012"),
    "algebra": UUID("00000000-0000-0000-0000-000000000021"),
    "arithmetic": UUID("00000000-0000-0000-0000-000000000022"),
    "gat_foundations": UUID("00000000-0000-0000-0000-000000000023"),
    "number_systems": UUID("00000000-0000-0000-0000-000000000031"),
    "linear_equations": UUID("00000000-0000-0000-0000-000000000032"),
    "fractions": UUID("00000000-0000-0000-0000-000000000033"),
    "basic_algebra": UUID("00000000-0000-0000-0000-000000000041"),
    "linear_expression": UUID("00000000-0000-0000-0000-000000000042"),
    "fraction_operations": UUID("00000000-0000-0000-0000-000000000043"),
    "equivalent_fractions": UUID("00000000-0000-0000-0000-000000000044"),
    "linear_prerequisite": UUID("00000000-0000-0000-0000-000000000061"),
}


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    exam_id = _ensure(
        connection,
        "exams",
        {"code": "NDA"},
        {"id": SEED_IDS["exam"], "name": "National Defence Academy", "code": "NDA", "description": "Starter curriculum for NDA preparation. Content should be reviewed before production use.", "is_active": True},
        now,
    )
    math_id = _ensure(connection, "subjects", {"exam_id": exam_id, "code": "MATH"}, {"id": SEED_IDS["math"], "exam_id": exam_id, "name": "Mathematics", "code": "MATH", "display_order": 1}, now)
    gat_id = _ensure(connection, "subjects", {"exam_id": exam_id, "code": "GAT"}, {"id": SEED_IDS["gat"], "exam_id": exam_id, "name": "General Ability Test", "code": "GAT", "display_order": 2}, now)

    algebra_id = _ensure(connection, "chapters", {"subject_id": math_id, "name": "Algebra"}, {"id": SEED_IDS["algebra"], "subject_id": math_id, "name": "Algebra", "description": "Expressions and equations used as a foundation for higher mathematics.", "display_order": 1}, now)
    arithmetic_id = _ensure(connection, "chapters", {"subject_id": math_id, "name": "Arithmetic"}, {"id": SEED_IDS["arithmetic"], "subject_id": math_id, "name": "Arithmetic", "description": "Number operations and foundational quantitative reasoning.", "display_order": 2}, now)
    _ensure(connection, "chapters", {"subject_id": gat_id, "name": "English and General Knowledge Foundations"}, {"id": SEED_IDS["gat_foundations"], "subject_id": gat_id, "name": "English and General Knowledge Foundations", "description": "Starter chapter reserved for reviewed GAT curriculum content.", "display_order": 1}, now)

    number_systems_id = _ensure(connection, "topics", {"chapter_id": arithmetic_id, "name": "Number Systems"}, {"id": SEED_IDS["number_systems"], "chapter_id": arithmetic_id, "name": "Number Systems", "description": "Types of numbers and their basic properties.", "display_order": 1}, now)
    linear_equations_id = _ensure(connection, "topics", {"chapter_id": algebra_id, "name": "Linear Equations"}, {"id": SEED_IDS["linear_equations"], "chapter_id": algebra_id, "name": "Linear Equations", "description": "Solving and interpreting one-variable linear equations.", "display_order": 1}, now)
    fractions_id = _ensure(connection, "topics", {"chapter_id": arithmetic_id, "name": "Fractions and Ratios"}, {"id": SEED_IDS["fractions"], "chapter_id": arithmetic_id, "name": "Fractions and Ratios", "description": "Fractions, ratios and operations required for later topics.", "display_order": 2}, now)

    basic_algebra_id = _ensure(connection, "concepts", {"topic_id": linear_equations_id, "name": "Basic Algebraic Operations"}, {"id": SEED_IDS["basic_algebra"], "topic_id": linear_equations_id, "name": "Basic Algebraic Operations", "description": "Combine like terms and apply inverse operations.", "display_order": 1}, now)
    linear_expression_id = _ensure(connection, "concepts", {"topic_id": linear_equations_id, "name": "Solving a Linear Equation"}, {"id": SEED_IDS["linear_expression"], "topic_id": linear_equations_id, "name": "Solving a Linear Equation", "description": "Solve a linear equation step by step and check the result.", "display_order": 2}, now)
    fraction_operations_id = _ensure(connection, "concepts", {"topic_id": fractions_id, "name": "Fraction Operations"}, {"id": SEED_IDS["fraction_operations"], "topic_id": fractions_id, "name": "Fraction Operations", "description": "Add, subtract, multiply and divide fractions.", "display_order": 1}, now)
    equivalent_fractions_id = _ensure(connection, "concepts", {"topic_id": fractions_id, "name": "Equivalent Fractions"}, {"id": SEED_IDS["equivalent_fractions"], "topic_id": fractions_id, "name": "Equivalent Fractions", "description": "Recognize equivalent fractions and simplify them.", "display_order": 2}, now)

    _ensure(
        connection,
        "prerequisites",
        {"concept_id": linear_expression_id, "prerequisite_concept_id": basic_algebra_id},
        {"id": SEED_IDS["linear_prerequisite"], "concept_id": linear_expression_id, "prerequisite_concept_id": basic_algebra_id, "is_required": True},
        now,
    )
    _ = (number_systems_id, fraction_operations_id, equivalent_fractions_id)


def _ensure(connection, table_name: str, lookup: dict[str, object], values: dict[str, object], now: datetime) -> UUID:
    where_clause = " AND ".join(f"{column} = :lookup_{column}" for column in lookup)
    parameters = {f"lookup_{column}": value for column, value in lookup.items()}
    existing_id = connection.execute(sa.text(f"SELECT id FROM {table_name} WHERE {where_clause} LIMIT 1"), parameters).scalar_one_or_none()
    if existing_id is not None:
        return existing_id

    values = {**values, "created_at": now, "updated_at": now}
    values = {key: _database_value(connection, value) for key, value in values.items()}
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    connection.execute(sa.text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"), values)
    return values["id"]


def _database_value(connection, value: object) -> object:
    """Bind UUIDs in a form accepted by both PostgreSQL and SQLite."""
    if isinstance(value, UUID) and connection.dialect.name == "sqlite":
        return value.hex
    return str(value) if isinstance(value, UUID) else value


def downgrade() -> None:
    connection = op.get_bind()
    for table_name in ("prerequisites", "concepts", "topics", "chapters", "subjects", "exams"):
        for item_id in SEED_IDS.values():
            connection.execute(sa.text(f"DELETE FROM {table_name} WHERE id = :item_id"), {"item_id": item_id})
