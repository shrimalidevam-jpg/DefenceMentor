"""Add persisted daily revision test attempts and question assignments."""

from alembic import op
import sqlalchemy as sa


revision = "20261001_0014"
down_revision = "20261001_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("daily_review_attempts"):
        op.create_table(
            "daily_review_attempts",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("plan_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
            sa.Column("question_count", sa.Integer(), nullable=False),
            sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "plan_date"),
        )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("daily_review_items"):
        op.create_table(
            "daily_review_items",
            sa.Column("attempt_id", sa.Uuid(), nullable=False),
            sa.Column("question_id", sa.Uuid(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("selected_option_id", sa.Uuid(), nullable=True),
            sa.Column("is_correct", sa.Boolean(), nullable=True),
            sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["attempt_id"], ["daily_review_attempts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["selected_option_id"], ["question_options.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("attempt_id", "question_id", name="uq_daily_review_item_question"),
            sa.UniqueConstraint("attempt_id", "position", name="uq_daily_review_item_position"),
        )

    inspector = sa.inspect(op.get_bind())
    for table, indexes in (
        ("daily_review_attempts", (
            ("ix_daily_review_attempts_user_id", "user_id"),
            ("ix_daily_review_attempts_plan_date", "plan_date"),
        )),
        ("daily_review_items", (
            ("ix_daily_review_items_attempt_id", "attempt_id"),
            ("ix_daily_review_items_question_id", "question_id"),
        )),
    ):
        existing_indexes = {index["name"] for index in inspector.get_indexes(table)}
        for name, column in indexes:
            if name not in existing_indexes:
                op.create_index(name, table, [column])


def downgrade() -> None:
    op.drop_index("ix_daily_review_items_question_id", table_name="daily_review_items")
    op.drop_index("ix_daily_review_items_attempt_id", table_name="daily_review_items")
    op.drop_table("daily_review_items")
    op.drop_index("ix_daily_review_attempts_plan_date", table_name="daily_review_attempts")
    op.drop_index("ix_daily_review_attempts_user_id", table_name="daily_review_attempts")
    op.drop_table("daily_review_attempts")
