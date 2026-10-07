"""Add persisted daily personalized study-plan tasks."""

from alembic import op
import sqlalchemy as sa


revision = "20261001_0013"
down_revision = "20260925_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("study_plan_tasks"):
        op.create_table(
            "study_plan_tasks",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("plan_date", sa.Date(), nullable=False),
            sa.Column("concept_id", sa.Uuid(), nullable=False),
            sa.Column("task_type", sa.String(30), nullable=False),
            sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="25"),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "plan_date", "concept_id", "task_type"),
        )
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("study_plan_tasks")}
    for name, column in (
        ("ix_study_plan_tasks_user_id", "user_id"),
        ("ix_study_plan_tasks_plan_date", "plan_date"),
        ("ix_study_plan_tasks_concept_id", "concept_id"),
    ):
        if name not in existing_indexes:
            op.create_index(name, "study_plan_tasks", [column])


def downgrade() -> None:
    op.drop_index("ix_study_plan_tasks_concept_id", table_name="study_plan_tasks")
    op.drop_index("ix_study_plan_tasks_plan_date", table_name="study_plan_tasks")
    op.drop_index("ix_study_plan_tasks_user_id", table_name="study_plan_tasks")
    op.drop_table("study_plan_tasks")
