"""Seed the reviewed Probability curriculum required by the learning MVP."""

from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from alembic import op


revision = "20260923_0008"
down_revision = "20260923_0007"
branch_labels = None
depends_on = None

TOPIC_ID = UUID("00000000-0000-0000-0000-000000000051")
CONCEPT_IDS = {
    "Basic Counting": UUID("00000000-0000-0000-0000-000000000052"),
    "Probability Basics": UUID("00000000-0000-0000-0000-000000000053"),
    "Probability": UUID("00000000-0000-0000-0000-000000000054"),
}
QUESTION_ID = UUID("00000000-0000-0000-0000-000000000121")
OPTION_IDS = (UUID("00000000-0000-0000-0000-000000000131"), UUID("00000000-0000-0000-0000-000000000132"))


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    chapter_id = connection.execute(sa.text("SELECT id FROM chapters WHERE name = 'Arithmetic' LIMIT 1")).scalar_one_or_none()
    subject_id = connection.execute(sa.text("SELECT subject_id FROM chapters WHERE id = :id"), {"id": chapter_id}).scalar_one_or_none() if chapter_id else None
    if not chapter_id or not subject_id:
        return
    topic_id = ensure(connection, "topics", {"id": TOPIC_ID, "chapter_id": chapter_id, "name": "Probability", "description": "Foundations of chance, outcomes and events.", "display_order": 3}, "chapter_id = :chapter_id AND name = :name", now)
    concepts = [
        ("Basic Counting", "Count equally likely outcomes before calculating probability."),
        ("Probability Basics", "Relate favourable outcomes to total equally likely outcomes."),
        ("Probability", "Apply probability rules to simple NDA-style questions."),
    ]
    ids = {}
    for name, description in concepts:
        ids[name] = ensure(connection, "concepts", {"id": CONCEPT_IDS[name], "topic_id": topic_id, "name": name, "description": description, "display_order": len(ids) + 1}, "topic_id = :topic_id AND name = :name", now)
    edge_id = UUID("00000000-0000-0000-0000-000000000055")
    connection.execute(sa.text("INSERT INTO prerequisites (id, concept_id, prerequisite_concept_id, is_required, created_at, updated_at) VALUES (:id, :concept_id, :prerequisite_concept_id, true, :created_at, :updated_at) ON CONFLICT DO NOTHING"), {"id": db_uuid(connection, edge_id), "concept_id": ids["Probability Basics"], "prerequisite_concept_id": ids["Basic Counting"], "created_at": now, "updated_at": now})
    connection.execute(sa.text("INSERT INTO prerequisites (id, concept_id, prerequisite_concept_id, is_required, created_at, updated_at) VALUES (:id, :concept_id, :prerequisite_concept_id, true, :created_at, :updated_at) ON CONFLICT DO NOTHING"), {"id": db_uuid(connection, UUID("00000000-0000-0000-0000-000000000056")), "concept_id": ids["Probability"], "prerequisite_concept_id": ids["Probability Basics"], "created_at": now, "updated_at": now})
    connection.execute(sa.text("INSERT INTO questions (id, exam_id, subject_id, topic_id, concept_id, question_text, question_type, difficulty, explanation, tags, is_published, created_at, updated_at) SELECT :id, e.id, :subject_id, :topic_id, :concept_id, :prompt, 'multiple_choice', 'easy', :explanation, 'phase10,reviewed-starter', true, :created_at, :updated_at FROM exams e WHERE e.code = 'NDA' ON CONFLICT DO NOTHING"), {"id": db_uuid(connection, QUESTION_ID), "subject_id": subject_id, "topic_id": topic_id, "concept_id": ids["Probability Basics"], "prompt": "A fair coin is tossed once. What is the probability of heads?", "explanation": "There is 1 favourable outcome among 2 equally likely outcomes, so the probability is 1/2.", "created_at": now, "updated_at": now})
    for position, option_id, text in ((1, OPTION_IDS[0], "1/2"), (2, OPTION_IDS[1], "1/3")):
        connection.execute(sa.text("INSERT INTO question_options (id, question_id, option_text, position, created_at, updated_at) VALUES (:id, :question_id, :text, :position, :created_at, :updated_at) ON CONFLICT DO NOTHING"), {"id": db_uuid(connection, option_id), "question_id": db_uuid(connection, QUESTION_ID), "text": text, "position": position, "created_at": now, "updated_at": now})
    connection.execute(sa.text("INSERT INTO question_answers (id, question_id, correct_option_id, created_at, updated_at) VALUES (:id, :question_id, :option_id, :created_at, :updated_at) ON CONFLICT (question_id) DO NOTHING"), {"id": db_uuid(connection, UUID("00000000-0000-0000-0000-000000000133")), "question_id": db_uuid(connection, QUESTION_ID), "option_id": db_uuid(connection, OPTION_IDS[0]), "created_at": now, "updated_at": now})


def ensure(connection, table: str, values: dict, lookup: str, now: datetime):
    existing = connection.execute(sa.text(f"SELECT id FROM {table} WHERE {lookup} LIMIT 1"), values).scalar_one_or_none()
    if existing:
        return existing
    values = {**values, "id": db_uuid(connection, values["id"]), "created_at": now, "updated_at": now}
    columns = ", ".join(values)
    connection.execute(sa.text(f"INSERT INTO {table} ({columns}) VALUES ({', '.join(':' + key for key in values)})"), values)
    return values["id"]


def db_uuid(connection, value):
    return value.hex if connection.dialect.name == "sqlite" and isinstance(value, UUID) else str(value) if isinstance(value, UUID) else value


def downgrade() -> None:
    pass