"""Save a new student's academic stream and Science group."""

from alembic import op
import sqlalchemy as sa


revision = "20261006_0022"
down_revision = "20261006_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("student_profiles")}
    if "academic_stream" not in columns:
        op.add_column("student_profiles", sa.Column("academic_stream", sa.String(length=20), nullable=True))
    if "science_group" not in columns:
        op.add_column("student_profiles", sa.Column("science_group", sa.String(length=1), nullable=True))


def downgrade() -> None:
    op.drop_column("student_profiles", "science_group")
    op.drop_column("student_profiles", "academic_stream")
