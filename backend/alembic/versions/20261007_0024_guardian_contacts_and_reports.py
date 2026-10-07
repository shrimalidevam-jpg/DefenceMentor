"""Add student and guardian contact details and progress report delivery records."""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0024"
down_revision = "20261006_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    profile_columns = {column["name"] for column in inspector.get_columns("student_profiles")}
    additions = (
        ("student_phone", sa.String(length=16)),
        ("parent_phone", sa.String(length=16)),
        ("student_photo", sa.LargeBinary()),
        ("parent_photo", sa.LargeBinary()),
        ("guardian_report_consent_at", sa.Date()),
    )
    for name, column_type in additions:
        if name not in profile_columns:
            op.add_column("student_profiles", sa.Column(name, column_type, nullable=True))

    if not inspector.has_table("parent_progress_reports"):
        op.create_table(
            "parent_progress_reports",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("period", sa.String(length=10), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "period", "period_start", name="uq_parent_report_user_period_start"),
        )
        inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("parent_progress_reports")}
    if "ix_parent_progress_reports_user_id" not in indexes:
        op.create_index("ix_parent_progress_reports_user_id", "parent_progress_reports", ["user_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("parent_progress_reports"):
        op.drop_index("ix_parent_progress_reports_user_id", table_name="parent_progress_reports")
        op.drop_table("parent_progress_reports")
    profile_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("student_profiles")}
    for name in ("guardian_report_consent_at", "parent_photo", "student_photo", "parent_phone", "student_phone"):
        if name in profile_columns:
            op.drop_column("student_profiles", name)
