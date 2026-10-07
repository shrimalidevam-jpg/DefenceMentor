"""Require learner study choices and seed starter GAT planning areas."""

from datetime import datetime, timezone
from uuid import UUID

from alembic import op
import sqlalchemy as sa


revision = "20261006_0020"
down_revision = "20261005_0019"
branch_labels = None
depends_on = None


GAT_AREAS = (
    ("English", "Reading comprehension, grammar and vocabulary"),
    ("Physics", "Motion, force and energy"),
    ("Chemistry", "Matter and chemical change"),
    ("General Science", "Biology and basic science"),
    ("History", "Indian history and culture"),
    ("Geography", "India and world geography"),
    ("Current Events", "Current affairs and defence awareness"),
)


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("student_profiles")}
    additions = (
        ("planner_setup_complete", sa.Boolean(), sa.false()),
        ("study_subjects", sa.Text(), "[]"),
        ("math_share_percent", sa.Integer(), "50"),
    )
    for name, column_type, default in additions:
        if name not in columns:
            op.add_column(
                "student_profiles",
                sa.Column(name, column_type, nullable=False, server_default=default),
            )

    connection = op.get_bind()
    gat_id = connection.execute(sa.text("SELECT id FROM subjects WHERE code = 'GAT' LIMIT 1")).scalar()
    if gat_id is None:
        return
    chapter_id = connection.execute(sa.text(
        "SELECT id FROM chapters WHERE subject_id = :subject_id AND name = 'English and General Knowledge Foundations' LIMIT 1"
    ), {"subject_id": gat_id}).scalar()
    if chapter_id is None:
        return

    topics = sa.table("topics", sa.column("id", sa.Uuid()), sa.column("chapter_id", sa.Uuid()), sa.column("name", sa.String()), sa.column("description", sa.Text()), sa.column("display_order", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    concepts = sa.table("concepts", sa.column("id", sa.Uuid()), sa.column("topic_id", sa.Uuid()), sa.column("name", sa.String()), sa.column("description", sa.Text()), sa.column("display_order", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)))
    now = datetime.now(timezone.utc)
    for index, (topic_name, concept_name) in enumerate(GAT_AREAS, start=1):
        topic_id = connection.execute(sa.select(topics.c.id).where(topics.c.chapter_id == chapter_id, topics.c.name == topic_name)).scalar()
        if topic_id is None:
            topic_id = UUID(f"00000000-0000-0000-0000-{100 + index:012d}")
            connection.execute(topics.insert().values(
                id=topic_id, chapter_id=chapter_id, name=topic_name,
                description=f"Starter GAT study area for {topic_name.lower()}.", display_order=index, created_at=now, updated_at=now,
            ))
        existing_concept = connection.execute(sa.select(concepts.c.id).where(concepts.c.topic_id == topic_id, concepts.c.name == concept_name)).scalar()
        if existing_concept is None:
            concept_id = UUID(f"00000000-0000-0000-0000-{200 + index:012d}")
            connection.execute(concepts.insert().values(
                id=concept_id, topic_id=topic_id, name=concept_name,
                description=f"Starter GAT planning concept: {concept_name.lower()}.", display_order=1, created_at=now, updated_at=now,
            ))


def downgrade() -> None:
    connection = op.get_bind()
    concept_ids = [UUID(f"00000000-0000-0000-0000-{200 + index:012d}") for index in range(1, len(GAT_AREAS) + 1)]
    topic_ids = [UUID(f"00000000-0000-0000-0000-{100 + index:012d}") for index in range(1, len(GAT_AREAS) + 1)]
    for concept_id in concept_ids:
        connection.execute(sa.text("DELETE FROM study_plan_tasks WHERE concept_id = :id"), {"id": concept_id})
        connection.execute(sa.text("DELETE FROM concepts WHERE id = :id"), {"id": concept_id})
    for topic_id in topic_ids:
        connection.execute(sa.text("DELETE FROM topics WHERE id = :id"), {"id": topic_id})
    op.drop_column("student_profiles", "math_share_percent")
    op.drop_column("student_profiles", "study_subjects")
    op.drop_column("student_profiles", "planner_setup_complete")
