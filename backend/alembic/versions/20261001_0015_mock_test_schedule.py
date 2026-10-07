"""Track weekly and monthly mock-test attempts."""

from alembic import op
import sqlalchemy as sa


revision = "20261001_0015"
down_revision = "20261001_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("assessment_attempts")}
    if "schedule_type" not in columns:
        op.add_column("assessment_attempts", sa.Column("schedule_type", sa.String(20), nullable=False, server_default="weekly"))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("assessment_attempts")}
    if "schedule_type" in columns:
        op.drop_column("assessment_attempts", "schedule_type")
