"""Track the start time of each timed NDA assessment section."""

from alembic import op
import sqlalchemy as sa


revision = "20261002_0017"
down_revision = "20261001_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("assessment_attempts")}
    if "section_started_at" not in columns:
        op.add_column(
            "assessment_attempts",
            sa.Column("section_started_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.execute(
            "UPDATE assessment_attempts SET section_started_at = started_at "
            "WHERE section_started_at IS NULL"
        )


def downgrade() -> None:
    op.drop_column("assessment_attempts", "section_started_at")
