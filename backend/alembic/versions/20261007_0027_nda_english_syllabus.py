"""Add the NDA GAT English syllabus to the curriculum."""

from datetime import datetime, timezone
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op


revision = "20261007_0027"
down_revision = "20261007_0026"
branch_labels = None
depends_on = None

NAMESPACE = UUID("9104dfcf-6011-4d63-a565-f31013a00272")

ENGLISH_TOPICS = (
    (
        "Spotting Errors",
        "Identify grammatical, usage and sentence-structure errors in written English.",
    ),
    (
        "Comprehension",
        "Understand passages, identify main ideas and details, and interpret meaning from context.",
    ),
    (
        "Selecting Words",
        "Choose suitable words to complete sentences accurately according to meaning and context.",
    ),
    (
        "Synonyms",
        "Recognise words with similar meanings and select contextually appropriate synonyms.",
    ),
    (
        "Antonyms",
        "Recognise words with opposite meanings and select contextually appropriate antonyms.",
    ),
    (
        "Sentence Improvements",
        "Improve sentence correctness, clarity and expression while preserving the intended meaning.",
    ),
    (
        "Ordering of Words in a Sentence",
        "Arrange words or groups of words into grammatically correct and meaningful sentences.",
    ),
)


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    gat_id = connection.execute(
        sa.text("SELECT id FROM subjects WHERE code = 'GAT' ORDER BY display_order LIMIT 1")
    ).scalar_one_or_none()
    if gat_id is None:
        return

    chapter_id = _ensure(
        connection,
        "chapters",
        {"subject_id": gat_id, "name": "English"},
        {
            "subject_id": gat_id,
            "name": "English",
            "description": "NDA General Ability Test English syllabus.",
            "display_order": 1,
        },
        now,
    )

    old_english_topic = connection.execute(
        sa.text(
            "SELECT topics.id FROM topics "
            "JOIN chapters ON chapters.id = topics.chapter_id "
            "WHERE chapters.subject_id = :gat_id AND topics.name = 'English' "
            "ORDER BY topics.display_order LIMIT 1"
        ),
        {"gat_id": gat_id},
    ).scalar_one_or_none()
    if old_english_topic is not None:
        connection.execute(
            sa.text(
                "UPDATE topics SET chapter_id = :chapter_id, name = 'English Foundations', "
                "display_order = 1, updated_at = :updated_at "
                "WHERE id = :topic_id"
            ),
            {
                "chapter_id": chapter_id,
                "updated_at": now,
                "topic_id": old_english_topic,
            },
        )
    for order, (name, description) in enumerate(ENGLISH_TOPICS, start=2):
        topic_id = _ensure(
            connection,
            "topics",
            {"chapter_id": chapter_id, "name": name},
            {
                "chapter_id": chapter_id,
                "name": name,
                "description": description,
                "display_order": order,
            },
            now,
        )
        _ensure(
            connection,
            "concepts",
            {"topic_id": topic_id, "name": name},
            {
                "topic_id": topic_id,
                "name": name,
                "description": description,
                "display_order": 1,
            },
            now,
        )


def _ensure(
    connection,
    table_name: str,
    lookup: dict[str, object],
    values: dict[str, object],
    now: datetime,
) -> object:
    where_clause = " AND ".join(f"{column} = :lookup_{column}" for column in lookup)
    parameters = {f"lookup_{column}": value for column, value in lookup.items()}
    existing_id = connection.execute(
        sa.text(f"SELECT id FROM {table_name} WHERE {where_clause} LIMIT 1"), parameters
    ).scalar_one_or_none()
    if existing_id is not None:
        return existing_id

    item_id = uuid5(
        NAMESPACE,
        f"{table_name}:{'|'.join(str(value) for value in lookup.values())}",
    )
    record = {**values, "id": _database_value(connection, item_id), "created_at": now, "updated_at": now}
    columns = ", ".join(record)
    placeholders = ", ".join(f":{column}" for column in record)
    connection.execute(
        sa.text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"),
        record,
    )
    return record["id"]


def _database_value(connection, value: object) -> object:
    if isinstance(value, UUID) and connection.dialect.name == "sqlite":
        return value.hex
    return str(value) if isinstance(value, UUID) else value


def downgrade() -> None:
    connection = op.get_bind()
    gat_id = connection.execute(
        sa.text("SELECT id FROM subjects WHERE code = 'GAT' ORDER BY display_order LIMIT 1")
    ).scalar_one_or_none()
    if gat_id is None:
        return
    english_chapter = connection.execute(
        sa.text("SELECT id FROM chapters WHERE subject_id = :gat_id AND name = 'English'"),
        {"gat_id": gat_id},
    ).scalar_one_or_none()
    foundation_chapter = connection.execute(
        sa.text("SELECT id FROM chapters WHERE subject_id = :gat_id AND name = 'English and General Knowledge Foundations'"),
        {"gat_id": gat_id},
    ).scalar_one_or_none()
    if english_chapter is None:
        return
    if foundation_chapter is not None:
        connection.execute(
            sa.text(
                "UPDATE topics SET chapter_id = :chapter_id, name = 'English' "
                "WHERE chapter_id = :english_chapter "
                "AND name = 'English Foundations'"
            ),
            {"chapter_id": foundation_chapter, "english_chapter": english_chapter},
        )
    for name, _ in ENGLISH_TOPICS:
        topic_id = uuid5(NAMESPACE, f"topics:{english_chapter}|{name}")
        stored_topic_id = _database_value(connection, topic_id)
        concept_id = uuid5(NAMESPACE, f"concepts:{stored_topic_id}|{name}")
        connection.execute(
            sa.text("DELETE FROM concepts WHERE id = :id"),
            {"id": _database_value(connection, concept_id)},
        )
        remaining_concepts = connection.execute(
            sa.text("SELECT 1 FROM concepts WHERE topic_id = :topic_id LIMIT 1"),
            {"topic_id": stored_topic_id},
        ).scalar_one_or_none()
        if remaining_concepts is None:
            connection.execute(
                sa.text("DELETE FROM topics WHERE id = :id"),
                {"id": stored_topic_id},
            )
    seeded_chapter_id = uuid5(NAMESPACE, f"chapters:{gat_id}|English")
    chapter_id_value = _database_value(connection, seeded_chapter_id)
    remaining_topics = connection.execute(
        sa.text("SELECT 1 FROM topics WHERE chapter_id = :chapter_id LIMIT 1"),
        {"chapter_id": chapter_id_value},
    ).scalar_one_or_none()
    if remaining_topics is None:
        connection.execute(
            sa.text("DELETE FROM chapters WHERE id = :id"),
            {"id": chapter_id_value},
        )
