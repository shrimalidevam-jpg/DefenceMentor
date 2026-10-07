"""Add Phase 11 adaptive assessment linkage and state."""

from alembic import op
import sqlalchemy as sa


revision = "20260924_0009"
down_revision = "20260923_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    attempt_columns = {column["name"] for column in inspector.get_columns("assessment_attempts")}
    if "current_round" not in attempt_columns:
        op.add_column("assessment_attempts", sa.Column("current_round", sa.String(30), nullable=False, server_default="easy"))
    if "current_question_id" not in attempt_columns:
        op.add_column("assessment_attempts", sa.Column("current_question_id", sa.Uuid(), nullable=True))
    if "answered_count" not in attempt_columns:
        op.add_column("assessment_attempts", sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"))
    question_columns = {column["name"] for column in inspector.get_columns("question_attempts")}
    if "assessment_attempt_id" not in question_columns:
        op.add_column("question_attempts", sa.Column("assessment_attempt_id", sa.Uuid(), nullable=True))
    if "assessment_round" not in question_columns:
        op.add_column("question_attempts", sa.Column("assessment_round", sa.String(30), nullable=True))
    if not any(foreign_key.get("name") == "fk_assessment_attempts_current_question_id_questions" for foreign_key in inspector.get_foreign_keys("assessment_attempts")):
        op.create_foreign_key("fk_assessment_attempts_current_question_id_questions", "assessment_attempts", "questions", ["current_question_id"], ["id"], ondelete="SET NULL")
    if not any(index["name"] == "ix_question_attempts_assessment_attempt_id" for index in inspector.get_indexes("question_attempts")):
        op.create_index("ix_question_attempts_assessment_attempt_id", "question_attempts", ["assessment_attempt_id"])


def downgrade() -> None:
    op.drop_constraint("fk_assessment_attempts_current_question_id_questions", "assessment_attempts", type_="foreignkey")
    op.drop_index("ix_question_attempts_assessment_attempt_id", table_name="question_attempts")
    op.drop_column("question_attempts", "assessment_round")
    op.drop_column("question_attempts", "assessment_attempt_id")
    op.drop_column("assessment_attempts", "answered_count")
    op.drop_column("assessment_attempts", "current_question_id")
    op.drop_column("assessment_attempts", "current_round")