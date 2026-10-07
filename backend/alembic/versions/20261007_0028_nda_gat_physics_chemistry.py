"""Add the NDA GAT Physics and Chemistry syllabus."""

from datetime import datetime, timezone
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op


revision = "20261007_0028"
down_revision = "20261007_0027"
branch_labels = None
depends_on = None

NAMESPACE = UUID("356c88c9-cc18-47df-8d6f-4e3b47acaa09")

SCIENCE_SYLLABUS = (
    (
        "Physics",
        "NDA General Ability Test Physics syllabus.",
        (
            (
                "Physical Properties and States of Matter",
                "Physical properties and states of matter; mass, weight, volume, density and specific gravity; Archimedes' principle and the pressure barometer.",
                (
                    ("Physical properties and states of matter", "Study the physical properties and states of matter."),
                    ("Mass, weight, volume, density and specific gravity", "Understand and distinguish mass, weight, volume, density and specific gravity."),
                    ("Archimedes' principle and pressure barometer", "Apply Archimedes' principle and understand the pressure barometer."),
                ),
            ),
            (
                "Motion, Force and Work, Power and Energy",
                "Motion, velocity and acceleration; Newton's laws; force and momentum; parallelogram of forces; stability and equilibrium; gravitation; work, power and energy.",
                (
                    ("Motion, velocity and acceleration", "Describe motion and use the concepts of velocity and acceleration."),
                    ("Newton's laws of motion", "State and apply Newton's laws of motion."),
                    ("Force, momentum and parallelogram of forces", "Understand force and momentum and combine forces using the parallelogram law."),
                    ("Stability and equilibrium of bodies", "Explain the stability and equilibrium of bodies."),
                    ("Gravitation", "Understand the elementary principles of gravitation."),
                    ("Work, power and energy", "Use the elementary ideas of work, power and energy."),
                ),
            ),
            (
                "Heat and Temperature",
                "Effects of heat; measurement of temperature and heat; change of state and latent heat; modes of heat transfer.",
                (
                    ("Effects and measurement of heat", "Describe the effects of heat and how temperature and heat are measured."),
                    ("Change of state and latent heat", "Explain changes of state and the role of latent heat."),
                    ("Modes of heat transfer", "Describe the modes by which heat is transferred."),
                ),
            ),
            (
                "Sound",
                "Sound waves and their properties, including simple musical instruments.",
                (
                    ("Sound waves and their properties", "Describe sound waves and their basic properties."),
                    ("Simple musical instruments", "Understand the elementary working principles of simple musical instruments."),
                ),
            ),
            (
                "Light and Optics",
                "Rectilinear propagation of light, reflection and refraction; spherical mirrors and lenses; the human eye.",
                (
                    ("Propagation, reflection and refraction of light", "Explain rectilinear propagation, reflection and refraction of light."),
                    ("Spherical mirrors and lenses", "Understand the basic properties and uses of spherical mirrors and lenses."),
                    ("Human eye", "Study the elementary structure and working of the human eye."),
                ),
            ),
            (
                "Magnetism",
                "Natural and artificial magnets; properties of a magnet; Earth as a magnet.",
                (
                    ("Natural and artificial magnets", "Distinguish natural and artificial magnets and describe their properties."),
                    ("Earth as a magnet", "Understand the Earth as a magnet."),
                ),
            ),
            (
                "Static and Current Electricity",
                "Static and current electricity; conductors and nonconductors; Ohm's law; simple electrical circuits; heating, lighting and magnetic effects of current; electrical power; primary and secondary cells.",
                (
                    ("Static and current electricity", "Understand the elementary ideas of static and current electricity."),
                    ("Conductors, nonconductors and Ohm's law", "Distinguish conductors from nonconductors and apply Ohm's law."),
                    ("Simple electrical circuits", "Understand and interpret simple electrical circuits."),
                    ("Effects of electric current", "Describe the heating, lighting and magnetic effects of current."),
                    ("Electrical power and cells", "Measure electrical power and distinguish primary and secondary cells."),
                ),
            ),
            (
                "Scientific Instruments, Devices and Electrical Safety",
                "General principles of the simple pendulum, pulleys, siphon, levers, balloon, pumps, hydrometer, pressure cooker, thermos flask, gramophone, telegraph, telephone, periscope, telescope, microscope and Mariner's compass; lightning conductors and safety fuses.",
                (
                    ("Simple machines and common devices", "Understand the general working principles of a simple pendulum, pulleys, siphon, levers, balloon, pumps, hydrometer, pressure cooker and thermos flask."),
                    ("Communication and optical instruments", "Understand the general working principles of the gramophone, telegraph, telephone, periscope, telescope and microscope."),
                    ("Mariner's compass and electrical safety", "Understand the Mariner's compass, lightning conductors and safety fuses."),
                ),
            ),
        ),
    ),
    (
        "Chemistry",
        "NDA General Ability Test Chemistry syllabus.",
        (
            (
                "Matter, Elements and Chemical Equations",
                "Physical and chemical changes; elements, mixtures and compounds; symbols, formulae and simple chemical equations.",
                (
                    ("Physical and chemical changes", "Distinguish physical changes from chemical changes."),
                    ("Elements, mixtures and compounds", "Identify and distinguish elements, mixtures and compounds."),
                    ("Symbols, formulae and simple chemical equations", "Use chemical symbols and formulae and interpret simple chemical equations."),
                ),
            ),
            (
                "Laws of Chemical Combination",
                "Laws of chemical combination, excluding problems.",
                (
                    ("Laws of chemical combination", "State and understand the laws of chemical combination; numerical problems are excluded."),
                ),
            ),
            (
                "Air and Water",
                "Properties of air and water.",
                (
                    ("Properties of air", "Study the properties and basic composition of air."),
                    ("Properties of water", "Study the properties of water."),
                ),
            ),
            (
                "Hydrogen, Oxygen, Nitrogen and Carbon Dioxide",
                "Preparation and properties of hydrogen, oxygen, nitrogen and carbon dioxide.",
                (
                    ("Hydrogen", "Study the preparation and properties of hydrogen."),
                    ("Oxygen", "Study the preparation and properties of oxygen."),
                    ("Nitrogen", "Study the preparation and properties of nitrogen."),
                    ("Carbon dioxide", "Study the preparation and properties of carbon dioxide."),
                ),
            ),
            (
                "Oxidation and Reduction",
                "Elementary concepts of oxidation and reduction.",
                (
                    ("Oxidation and reduction", "Understand the elementary ideas of oxidation and reduction."),
                ),
            ),
            (
                "Acids, Bases and Salts",
                "Acids, bases and salts.",
                (
                    ("Acids, bases and salts", "Identify acids, bases and salts and understand their elementary properties."),
                ),
            ),
            (
                "Carbon and Its Different Forms",
                "Carbon and its different forms.",
                (
                    ("Different forms of carbon", "Study carbon and recognise its different forms."),
                ),
            ),
            (
                "Fertilizers",
                "Natural and artificial fertilizers.",
                (
                    ("Natural and artificial fertilizers", "Distinguish natural and artificial fertilizers and understand their uses."),
                ),
            ),
            (
                "Common Materials and Their Preparation",
                "Materials used in preparing soap, glass, ink, paper, cement, paints, safety matches and gunpowder.",
                (
                    ("Soap, glass, ink and paper", "Study the materials used in the preparation of soap, glass, ink and paper."),
                    ("Cement, paints, safety matches and gunpowder", "Study the materials used in the preparation of cement, paints, safety matches and gunpowder."),
                ),
            ),
            (
                "Atomic Structure and Chemical Quantities",
                "Elementary ideas about atomic structure, atomic equivalents, molecular weights and valency.",
                (
                    ("Structure of the atom", "Understand elementary ideas about the structure of the atom."),
                    ("Atomic equivalents and molecular weights", "Understand atomic equivalents and molecular weights."),
                    ("Valency", "Understand and use the concept of valency."),
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
    for chapter_order, (chapter_name, chapter_description, topics) in enumerate(SCIENCE_SYLLABUS, start=2):
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
        for topic_order, (topic_name, topic_description, concepts) in enumerate(topics, start=1):
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

    for chapter_name, _, topics in SCIENCE_SYLLABUS:
        chapter_id = connection.execute(
            sa.text("SELECT id FROM chapters WHERE subject_id = :subject_id AND name = :name"),
            {"subject_id": gat_id, "name": chapter_name},
        ).scalar_one_or_none()
        if chapter_id is None:
            continue
        stored_chapter_id = _database_value(connection, chapter_id)
        for topic_name, _, concepts in topics:
            topic_id = connection.execute(
                sa.text("SELECT id FROM topics WHERE chapter_id = :chapter_id AND name = :name"),
                {"chapter_id": chapter_id, "name": topic_name},
            ).scalar_one_or_none()
            if topic_id is None:
                continue
            stored_topic_id = _database_value(connection, topic_id)
            for concept_name, _ in concepts:
                concept_id = uuid5(
                    NAMESPACE,
                    f"concepts:{'|'.join(str(value) for value in (stored_topic_id, concept_name))}",
                )
                connection.execute(
                    sa.text("DELETE FROM concepts WHERE id = :id"),
                    {"id": _database_value(connection, concept_id)},
                )
            remaining_concepts = connection.execute(
                sa.text("SELECT 1 FROM concepts WHERE topic_id = :topic_id LIMIT 1"),
                {"topic_id": stored_topic_id},
            ).scalar_one_or_none()
            seeded_topic_id = uuid5(
                NAMESPACE,
                f"topics:{'|'.join(str(value) for value in (stored_chapter_id, topic_name))}",
            )
            if remaining_concepts is None and stored_topic_id == _database_value(connection, seeded_topic_id):
                connection.execute(
                    sa.text("DELETE FROM topics WHERE id = :id"),
                    {"id": stored_topic_id},
                )
        remaining_topics = connection.execute(
            sa.text("SELECT 1 FROM topics WHERE chapter_id = :chapter_id LIMIT 1"),
            {"chapter_id": stored_chapter_id},
        ).scalar_one_or_none()
        seeded_chapter_id = uuid5(
            NAMESPACE,
            f"chapters:{'|'.join(str(value) for value in (gat_id, chapter_name))}",
        )
        if remaining_topics is None and stored_chapter_id == _database_value(connection, seeded_chapter_id):
            connection.execute(
                sa.text("DELETE FROM chapters WHERE id = :id"),
                {"id": stored_chapter_id},
            )
