"""Align legacy assessment tables with the adaptive assessment models."""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0011"
down_revision = "20260925_0010"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    assessment_columns = _columns("assessments")
    if "title" not in assessment_columns:
        op.add_column("assessments", sa.Column("title", sa.String(180), nullable=True))
    if "time_limit_seconds" not in assessment_columns:
        op.add_column("assessments", sa.Column("time_limit_seconds", sa.Integer(), nullable=True))
    if "user_id" in assessment_columns:
        op.alter_column("assessments", "user_id", nullable=True)
    if "status" in assessment_columns:
        op.alter_column("assessments", "status", nullable=True)

    attempt_columns = _columns("assessment_attempts")
    if "status" not in attempt_columns:
        op.add_column("assessment_attempts", sa.Column("status", sa.String(30), nullable=False, server_default="in_progress"))
    if "started_at" not in attempt_columns:
        op.add_column("assessment_attempts", sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    if "completed_at" not in attempt_columns:
        op.add_column("assessment_attempts", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    question_attempt_columns = _columns("question_attempts")
    if "attempted_at" in question_attempt_columns:
        op.alter_column("question_attempts", "attempted_at", server_default=sa.text("now()"), nullable=True)
    if "hints_used" in question_attempt_columns:
        op.alter_column("question_attempts", "hints_used", server_default="0", nullable=True)


def downgrade() -> None:
    question_attempt_columns = _columns("question_attempts")
    if "hints_used" in question_attempt_columns:
        op.alter_column("question_attempts", "hints_used", server_default=None, nullable=False)
    if "attempted_at" in question_attempt_columns:
        op.alter_column("question_attempts", "attempted_at", server_default=None, nullable=False)

    attempt_columns = _columns("assessment_attempts")
    if "completed_at" in attempt_columns:
        op.drop_column("assessment_attempts", "completed_at")
    if "started_at" in attempt_columns:
        op.drop_column("assessment_attempts", "started_at")
    if "status" in attempt_columns:
        op.drop_column("assessment_attempts", "status")

    assessment_columns = _columns("assessments")
    if "time_limit_seconds" in assessment_columns:
        op.drop_column("assessments", "time_limit_seconds")
    if "title" in assessment_columns:
        op.drop_column("assessments", "title")
    if "status" in assessment_columns:
        op.alter_column("assessments", "status", nullable=False)
    if "user_id" in assessment_columns:
        op.alter_column("assessments", "user_id", nullable=False)
