"""Persist question order for navigable assessment attempts."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from alembic import op
import sqlalchemy as sa


revision = "20261002_0018"
down_revision = "20261002_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_exists = inspector.has_table("assessment_question_assignments")
    if not table_exists:
        op.create_table(
            "assessment_question_assignments",
            sa.Column("attempt_id", sa.Uuid(), nullable=False),
            sa.Column("question_id", sa.Uuid(), nullable=False),
            sa.Column("section_name", sa.String(length=30), nullable=False),
            sa.Column("display_order", sa.Integer(), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["attempt_id"], ["assessment_attempts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "attempt_id",
                "question_id",
                name="uq_assessment_assignment_attempt_question",
            ),
            sa.UniqueConstraint(
                "attempt_id",
                "section_name",
                "display_order",
                name="uq_assessment_assignment_attempt_section_order",
            ),
        )
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("assessment_question_assignments")}
    for name, column in (
        ("ix_assessment_question_assignments_attempt_id", "attempt_id"),
        ("ix_assessment_question_assignments_question_id", "question_id"),
        ("ix_assessment_question_assignments_section_name", "section_name"),
    ):
        if name not in existing_indexes:
            op.create_index(name, "assessment_question_assignments", [column])
    if table_exists:
        return
    connection = op.get_bind()
    assignments = sa.table(
        "assessment_question_assignments",
        sa.column("attempt_id", sa.Uuid()),
        sa.column("question_id", sa.Uuid()),
        sa.column("section_name", sa.String()),
        sa.column("display_order", sa.Integer()),
        sa.column("id", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    active_attempts = connection.execute(sa.text(
        "SELECT aa.id, aa.current_round, aa.current_question_id "
        "FROM assessment_attempts aa "
        "JOIN assessments a ON a.id = aa.assessment_id "
        "WHERE aa.status = 'in_progress' AND a.assessment_type = 'nda-mock'"
    )).mappings()
    now = datetime.now(timezone.utc)
    for attempt in active_attempts:
        attempt_id = UUID(str(attempt["id"]))
        question_attempts = connection.execute(sa.text(
            "SELECT question_id, assessment_round FROM question_attempts "
            "WHERE assessment_attempt_id = :attempt_id "
            "ORDER BY attempted_at, id"
        ), {"attempt_id": attempt["id"]}).mappings()
        section_questions: dict[str, list[UUID]] = {"MATH": [], "GAT": []}
        for question_attempt in question_attempts:
            section = question_attempt["assessment_round"] or attempt["current_round"]
            question_id = UUID(str(question_attempt["question_id"]))
            if section in section_questions and question_id not in section_questions[section]:
                section_questions[section].append(question_id)
        current_question_id = attempt["current_question_id"]
        current_section = attempt["current_round"]
        if current_section in section_questions and current_question_id is not None:
            current_id = UUID(str(current_question_id))
            if current_id not in section_questions[current_section]:
                section_questions[current_section].append(current_id)
        rows = []
        for section, question_ids in section_questions.items():
            rows.extend({
                "attempt_id": attempt_id,
                "question_id": question_id,
                "section_name": section,
                "display_order": order,
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
            } for order, question_id in enumerate(question_ids, start=1))
        if rows:
            connection.execute(assignments.insert(), rows)


def downgrade() -> None:
    op.drop_index("ix_assessment_question_assignments_section_name", table_name="assessment_question_assignments")
    op.drop_index("ix_assessment_question_assignments_question_id", table_name="assessment_question_assignments")
    op.drop_index("ix_assessment_question_assignments_attempt_id", table_name="assessment_question_assignments")
    op.drop_table("assessment_question_assignments")
