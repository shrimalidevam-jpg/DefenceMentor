"""Seed reviewed starter questions for the Phase 8 diagnostic engine."""

from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from alembic import op


revision = "20260923_0005"
down_revision = "20260923_0004"
branch_labels = None
depends_on = None

QUESTION_IDS = (
    UUID("00000000-0000-0000-0000-000000000101"),
    UUID("00000000-0000-0000-0000-000000000102"),
    UUID("00000000-0000-0000-0000-000000000103"),
)
OPTION_IDS = (
    UUID("00000000-0000-0000-0000-000000000111"),
    UUID("00000000-0000-0000-0000-000000000112"),
    UUID("00000000-0000-0000-0000-000000000113"),
    UUID("00000000-0000-0000-0000-000000000114"),
    UUID("00000000-0000-0000-0000-000000000115"),
    UUID("00000000-0000-0000-0000-000000000116"),
)


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    exam_id = connection.execute(sa.text("SELECT id FROM exams WHERE code = 'NDA' LIMIT 1")).scalar_one_or_none()
    subject_id = connection.execute(sa.text("SELECT id FROM subjects WHERE code = 'MATH' LIMIT 1")).scalar_one_or_none()
    topic_id = connection.execute(sa.text("SELECT id FROM topics WHERE name = 'Probability' LIMIT 1")).scalar_one_or_none()
    concepts = connection.execute(
        sa.text("SELECT id, name FROM concepts WHERE name IN ('Basic Counting', 'Fractions and Ratios', 'Probability Basics')")
    ).all()
    concept_ids = {name: concept_id for concept_id, name in concepts}
    if not exam_id or not subject_id or not topic_id or len(concept_ids) < 3:
        return

    questions = [
        (QUESTION_IDS[0], concept_ids["Basic Counting"], "A box contains 3 red and 2 blue balls. How many balls are in the box?", "Count all outcomes: 3 + 2 = 5.", "5", ("5", "6")),
        (QUESTION_IDS[1], concept_ids["Fractions and Ratios"], "Which fraction is equivalent to 1/2?", "Multiplying numerator and denominator by 2 gives 2/4.", "2/4", ("2/4", "1/3")),
        (QUESTION_IDS[2], concept_ids["Probability Basics"], "A fair coin is tossed once. What is the probability of heads?", "There is 1 favourable outcome among 2 equally likely outcomes.", "1/2", ("1/2", "1/3")),
    ]
    for question_id, concept_id, prompt, explanation, correct_text, options in questions:
        connection.execute(
            sa.text("""
                INSERT INTO questions (id, exam_id, subject_id, topic_id, concept_id, question_text, question_type, difficulty, explanation, tags, is_published, created_at, updated_at)
                VALUES (:id, :exam_id, :subject_id, :topic_id, :concept_id, :question_text, 'multiple_choice', 'easy', :explanation, 'phase8,reviewed-starter', true, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {"id": db_uuid(connection, question_id), "exam_id": exam_id, "subject_id": subject_id, "topic_id": topic_id, "concept_id": concept_id, "question_text": prompt, "explanation": explanation, "created_at": now, "updated_at": now},
        )

    option_index = 0
    for question_id, _, _, _, _, options in questions:
        option_ids = OPTION_IDS[option_index:option_index + 2]
        for position, (option_id, option_text) in enumerate(zip(option_ids, options), start=1):
            connection.execute(
                sa.text("""
                    INSERT INTO question_options (id, question_id, option_text, position, created_at, updated_at)
                    VALUES (:id, :question_id, :option_text, :position, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                {"id": db_uuid(connection, option_id), "question_id": db_uuid(connection, question_id), "option_text": option_text, "position": position, "created_at": now, "updated_at": now},
            )
        connection.execute(
            sa.text("""
                INSERT INTO question_answers (id, question_id, correct_option_id, correct_text, created_at, updated_at)
                VALUES (:id, :question_id, :correct_option_id, :correct_text, :created_at, :updated_at)
                ON CONFLICT (question_id) DO NOTHING
            """),
            {"id": db_uuid(connection, UUID(int=question_id.int + 1000)), "question_id": db_uuid(connection, question_id), "correct_option_id": db_uuid(connection, option_ids[0]), "correct_text": None, "created_at": now, "updated_at": now},
        )
        option_index += 2


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM question_answers WHERE question_id IN :ids"), {"ids": QUESTION_IDS})
    connection.execute(sa.text("DELETE FROM question_options WHERE question_id IN :ids"), {"ids": QUESTION_IDS})
    connection.execute(sa.text("DELETE FROM questions WHERE id IN :ids"), {"ids": QUESTION_IDS})


def db_uuid(connection, value: UUID) -> str:
    return value.hex if connection.dialect.name == "sqlite" else str(value)
