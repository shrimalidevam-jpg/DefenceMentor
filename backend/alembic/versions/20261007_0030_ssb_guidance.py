"""Persist daily SSB coaching and SSB-specific chat."""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0030"
down_revision = "20261007_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_ssb_guidance",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("guidance_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("guidance", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("reflection_question", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "guidance_date", name="uq_daily_ssb_guidance_user_date"),
    )
    op.create_index("ix_daily_ssb_guidance_user_id", "daily_ssb_guidance", ["user_id"])
    op.create_index("ix_daily_ssb_guidance_guidance_date", "daily_ssb_guidance", ["guidance_date"])
    op.create_table(
        "ssb_guidance_messages",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssb_guidance_messages_user_id", "ssb_guidance_messages", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ssb_guidance_messages_user_id", table_name="ssb_guidance_messages")
    op.drop_table("ssb_guidance_messages")
    op.drop_index("ix_daily_ssb_guidance_guidance_date", table_name="daily_ssb_guidance")
    op.drop_index("ix_daily_ssb_guidance_user_id", table_name="daily_ssb_guidance")
    op.drop_table("daily_ssb_guidance")
