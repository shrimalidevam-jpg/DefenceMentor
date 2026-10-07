"""Add confidence evidence to Phase 10 mastery calculations."""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0007"
down_revision = "20260923_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "confidence" not in {column["name"] for column in inspector.get_columns("question_attempts")}:
        op.add_column("question_attempts", sa.Column("confidence", sa.Numeric(3, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("question_attempts", "confidence")