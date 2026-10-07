"""Add student-controlled adaptive study-day preferences."""

from alembic import op
import sqlalchemy as sa


revision = "20261005_0019"
down_revision = "20261002_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("student_profiles")}
    additions = (
        ("daily_study_minutes", sa.Integer(), "360"),
        ("study_start_time", sa.String(length=5), "08:00"),
        ("focus_session_minutes", sa.Integer(), "50"),
        ("break_minutes", sa.Integer(), "10"),
    )
    for name, column_type, default in additions:
        if name not in columns:
            op.add_column(
                "student_profiles",
                sa.Column(name, column_type, nullable=False, server_default=default),
            )


def downgrade() -> None:
    op.drop_column("student_profiles", "break_minutes")
    op.drop_column("student_profiles", "focus_session_minutes")
    op.drop_column("student_profiles", "study_start_time")
    op.drop_column("student_profiles", "daily_study_minutes")
