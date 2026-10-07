"""Expand NDA GAT General Science, History, Geography and Current Events."""

from datetime import datetime, timezone
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op


revision = "20261007_0029"
down_revision = "20261007_0028"
branch_labels = None
depends_on = None

NAMESPACE = UUID("7ef6e17d-d229-4db1-8c18-88b0f7af68b8")
FOUNDATION_CHAPTER = "English and General Knowledge Foundations"
FOUNDATION_CONCEPTS = {
    "General Science": "Biology and basic science",
    "History": "Indian history and culture",
    "Geography": "India and world geography",
    "Current Events": "Current affairs and defence awareness",
}

GAT_SYLLABUS = (
    (
        "General Science",
        "NDA General Ability Test General Science syllabus.",
        (
            (
                "Living and Non-living Things",
                "Differences between living and non-living things; cells, protoplasm and tissues.",
                (
                    ("Living and non-living things", "Explain the differences between living and non-living things."),
                    ("Cells and protoplasm", "Understand cells as the basis of life and describe protoplasm at an elementary level."),
                    ("Tissues", "Understand the elementary organisation and role of tissues."),
                ),
            ),
            (
                "Growth and Reproduction",
                "Growth and reproduction in plants and animals.",
                (
                    ("Growth in plants and animals", "Describe the basic processes of growth in plants and animals."),
                    ("Reproduction in plants and animals", "Understand the elementary processes of reproduction in plants and animals."),
                ),
            ),
            (
                "Human Body and Health",
                "Elementary knowledge of the human body and its vital organs; common epidemics, their causes and prevention.",
                (
                    ("Human body and vital organs", "Identify the major vital organs and understand their basic functions."),
                    ("Common epidemics", "Recognise common epidemics and understand their causes and prevention."),
                ),
            ),
            (
                "Food, Nutrition and the Solar System",
                "Food as a source of energy and its constituents, including a balanced diet; the Solar System, meteors, comets and eclipses.",
                (
                    ("Food, energy and balanced diet", "Understand food as a source of energy, its constituents and the principles of a balanced diet."),
                    ("Solar System, meteors and comets", "Study the Solar System and identify meteors and comets."),
                    ("Eclipses", "Understand the basic causes of eclipses."),
                ),
            ),
            (
                "Eminent Scientists and Achievements",
                "Eminent scientists and their achievements.",
                (
                    ("Scientists and their achievements", "Recognise eminent scientists and important achievements in science."),
                ),
            ),
        ),
    ),
    (
        "History",
        "NDA General Ability Test History syllabus, including Indian history, the freedom movement and forces shaping the modern world.",
        (
            (
                "Indian History, Culture and Civilisation",
                "A broad survey of Indian History, with emphasis on culture and civilisation.",
                (
                    ("Indian history", "Study a broad survey of the major periods and developments in Indian history."),
                    ("Indian culture and civilisation", "Understand important features of Indian culture and civilisation."),
                ),
            ),
            (
                "Freedom Movement, Constitution and Administration",
                "Freedom Movement in India; elementary study of the Indian Constitution and administration.",
                (
                    ("Freedom Movement in India", "Study the major events, people and ideas of India's freedom movement."),
                    ("Indian Constitution and administration", "Understand elementary features of the Indian Constitution and system of administration."),
                ),
            ),
            (
                "Development, Social Welfare and National Integration",
                "Elementary knowledge of Five Year Plans, Panchayati Raj, co-operatives, community development, Bhoodan, Sarvodaya, national integration and the welfare state; basic teachings of Mahatma Gandhi.",
                (
                    ("Plans and community development", "Understand Five Year Plans, Panchayati Raj, co-operatives and community development at an elementary level."),
                    ("Bhoodan, Sarvodaya and the welfare state", "Study the ideas of Bhoodan, Sarvodaya and the welfare state."),
                    ("National integration and Mahatma Gandhi", "Understand national integration and the basic teachings of Mahatma Gandhi."),
                ),
            ),
            (
                "Modern World and Political Ideas",
                "Renaissance, Exploration and Discovery, American, French, Industrial and Russian Revolutions; impact of science and technology on society; concept of one world, United Nations, Panchsheel, democracy, socialism, communism and India's role in the present world.",
                (
                    ("Renaissance and Exploration", "Study the Renaissance and the age of exploration and discovery."),
                    ("Revolutions and the modern world", "Understand the American, French, Industrial and Russian Revolutions and their influence."),
                    ("Science, technology and society", "Understand the impact of science and technology on society."),
                    ("United Nations and international ideas", "Study the concept of one world, the United Nations and Panchsheel."),
                    ("Democracy, socialism and communism", "Understand the elementary principles of democracy, socialism and communism."),
                    ("India in the present world", "Understand India's role in the present world."),
                ),
            ),
        ),
    ),
    (
        "Geography",
        "NDA General Ability Test Geography syllabus covering physical geography, climate, resources and India.",
        (
            (
                "Earth, Coordinates and Time",
                "The Earth, its shape and size; latitudes and longitudes; concept of time and the International Date Line; movements of the Earth and their effects.",
                (
                    ("Shape and size of the Earth", "Understand the shape and size of the Earth."),
                    ("Latitudes and longitudes", "Locate places using latitudes and longitudes."),
                    ("Time and the International Date Line", "Understand time zones and the purpose of the International Date Line."),
                    ("Movements of the Earth", "Describe the Earth's movements and their effects."),
                ),
            ),
            (
                "Earth's Origin, Rocks and Landforms",
                "Origin of the Earth; rocks and their classification; mechanical and chemical weathering; earthquakes and volcanoes.",
                (
                    ("Origin of the Earth", "Study elementary explanations of the origin of the Earth."),
                    ("Rocks and their classification", "Identify and classify the main types of rocks."),
                    ("Mechanical and chemical weathering", "Distinguish mechanical weathering from chemical weathering."),
                    ("Earthquakes and volcanoes", "Understand the causes and basic features of earthquakes and volcanoes."),
                ),
            ),
            (
                "Oceans and the Atmosphere",
                "Ocean currents and tides; composition of the atmosphere; temperature and atmospheric pressure; planetary winds, cyclones and anti-cyclones.",
                (
                    ("Ocean currents and tides", "Study ocean currents and tides and their basic effects."),
                    ("Composition of the atmosphere", "Understand the composition of the atmosphere."),
                    ("Temperature and atmospheric pressure", "Understand temperature and atmospheric pressure."),
                    ("Planetary winds and cyclones", "Study planetary winds, cyclones and anti-cyclones."),
                ),
            ),
            (
                "Weather, Climate and Natural Regions",
                "Humidity, condensation and precipitation; types of climate and major natural regions of the world.",
                (
                    ("Humidity, condensation and precipitation", "Understand humidity, condensation and precipitation."),
                    ("Types of climate", "Identify major types of climate."),
                    ("Natural regions of the world", "Describe the major natural regions of the world."),
                ),
            ),
            (
                "Regional Geography of India",
                "Climate and natural vegetation of India; mineral and power resources; location and distribution of agricultural and industrial activities.",
                (
                    ("Indian climate and natural vegetation", "Study India's climate and natural vegetation."),
                    ("Mineral and power resources", "Identify the distribution and importance of India's mineral and power resources."),
                    ("Agriculture and industry in India", "Study the location and distribution of agricultural and industrial activities in India."),
                ),
            ),
            (
                "Transport, Trade and Exports of India",
                "Important sea ports and main sea, land and air routes of India; main items of imports and exports.",
                (
                    ("Sea ports and transport routes", "Locate important sea ports and describe India's main sea, land and air routes."),
                    ("Imports and exports", "Identify the main items imported and exported by India."),
                ),
            ),
        ),
    ),
    (
        "Current Events",
        "NDA General Ability Test current events and current affairs syllabus.",
        (
            (
                "Recent Events in India and the World",
                "Important events that have happened in India in recent years and important current world events.",
                (
                    ("Recent events in India", "Follow and understand important events that have happened in India in recent years."),
                    ("Current world events", "Follow and understand important current events around the world."),
                ),
            ),
            (
                "Prominent Personalities",
                "Prominent Indian and international personalities, including those connected with cultural activities and sports.",
                (
                    ("Indian personalities", "Recognise prominent Indian personalities and their contributions."),
                    ("International personalities", "Recognise prominent international personalities and their contributions."),
                    ("Culture and sports", "Follow prominent personalities connected with cultural activities and sports."),
                ),
            ),
        ),
    ),
)


def upgrade() -> None:
    connection = op.get_bind()
    gat_id = connection.execute(
        sa.text("SELECT id FROM subjects WHERE code = 'GAT' ORDER BY display_order LIMIT 1")
    ).scalar_one_or_none()
    if gat_id is None:
        return

    now = datetime.now(timezone.utc)
    for chapter_order, (chapter_name, chapter_description, topics) in enumerate(GAT_SYLLABUS, start=4):
        chapter_id = _ensure(
            connection,
            "chapters",
            {"subject_id": gat_id, "name": chapter_name},
            {
                "subject_id": gat_id,
                "name": chapter_name,
                "description": chapter_description,
                "display_order": chapter_order,
            },
            now,
        )
        old_topic_id = connection.execute(
            sa.text(
                "SELECT topics.id FROM topics "
                "JOIN chapters ON chapters.id = topics.chapter_id "
                "WHERE chapters.subject_id = :gat_id "
                "AND chapters.name = :foundation_chapter "
                "AND topics.name = :topic_name LIMIT 1"
            ),
            {
                "gat_id": gat_id,
                "foundation_chapter": FOUNDATION_CHAPTER,
                "topic_name": chapter_name,
            },
        ).scalar_one_or_none()
        if old_topic_id is not None:
            connection.execute(
                sa.text(
                    "UPDATE topics SET chapter_id = :chapter_id, name = :foundation_name, "
                    "display_order = 1, updated_at = :updated_at WHERE id = :topic_id"
                ),
                {
                    "chapter_id": chapter_id,
                    "foundation_name": f"{chapter_name} Foundations",
                    "updated_at": now,
                    "topic_id": old_topic_id,
                },
            )

        for topic_order, (topic_name, topic_description, concepts) in enumerate(topics, start=2):
            topic_id = _ensure(
                connection,
                "topics",
                {"chapter_id": chapter_id, "name": topic_name},
                {
                    "chapter_id": chapter_id,
                    "name": topic_name,
                    "description": topic_description,
                    "display_order": topic_order,
                },
                now,
            )
            for concept_order, (concept_name, concept_description) in enumerate(concepts, start=1):
                _ensure(
                    connection,
                    "concepts",
                    {"topic_id": topic_id, "name": concept_name},
                    {
                        "topic_id": topic_id,
                        "name": concept_name,
                        "description": concept_description,
                        "display_order": concept_order,
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

    for chapter_name, _, topics in GAT_SYLLABUS:
        chapter_id = connection.execute(
            sa.text("SELECT id FROM chapters WHERE subject_id = :subject_id AND name = :name"),
            {"subject_id": gat_id, "name": chapter_name},
        ).scalar_one_or_none()
        if chapter_id is None:
            continue
        stored_chapter_id = _database_value(connection, chapter_id)
        foundation_name = f"{chapter_name} Foundations"
        foundation_chapter_id = connection.execute(
            sa.text("SELECT id FROM chapters WHERE subject_id = :subject_id AND name = :name"),
            {"subject_id": gat_id, "name": FOUNDATION_CHAPTER},
        ).scalar_one_or_none()
        if foundation_chapter_id is not None:
            connection.execute(
                sa.text(
                    "UPDATE topics SET chapter_id = :foundation_chapter, name = :original_name "
                    "WHERE chapter_id = :chapter_id AND name = :foundation_name "
                    "AND id IN (SELECT topic_id FROM concepts WHERE name = :concept_name)"
                ),
                {
                    "foundation_chapter": foundation_chapter_id,
                    "original_name": chapter_name,
                    "chapter_id": chapter_id,
                    "foundation_name": foundation_name,
                    "concept_name": FOUNDATION_CONCEPTS[chapter_name],
                },
            )
        for topic_name, _, concepts in topics:
            topic_id = connection.execute(
                sa.text("SELECT id FROM topics WHERE chapter_id = :chapter_id AND name = :name"),
                {"chapter_id": chapter_id, "name": topic_name},
            ).scalar_one_or_none()
            if topic_id is None:
                continue
            stored_topic_id = _database_value(connection, topic_id)
            for concept_name, _ in concepts:
                concept_id = uuid5(NAMESPACE, f"concepts:{stored_topic_id}|{concept_name}")
                connection.execute(
                    sa.text("DELETE FROM concepts WHERE id = :id"),
                    {"id": _database_value(connection, concept_id)},
                )
            remaining_concepts = connection.execute(
                sa.text("SELECT 1 FROM concepts WHERE topic_id = :topic_id LIMIT 1"),
                {"topic_id": stored_topic_id},
            ).scalar_one_or_none()
            seeded_topic_id = uuid5(NAMESPACE, f"topics:{stored_chapter_id}|{topic_name}")
            if remaining_concepts is None and stored_topic_id == _database_value(connection, seeded_topic_id):
                connection.execute(sa.text("DELETE FROM topics WHERE id = :id"), {"id": stored_topic_id})

        remaining_topics = connection.execute(
            sa.text("SELECT 1 FROM topics WHERE chapter_id = :chapter_id LIMIT 1"),
            {"chapter_id": stored_chapter_id},
        ).scalar_one_or_none()
        seeded_chapter_id = uuid5(NAMESPACE, f"chapters:{gat_id}|{chapter_name}")
        if remaining_topics is None and stored_chapter_id == _database_value(connection, seeded_chapter_id):
            connection.execute(sa.text("DELETE FROM chapters WHERE id = :id"), {"id": stored_chapter_id})
