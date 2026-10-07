"""Persist student attempts for the daily vocabulary quiz."""

from alembic import op
import sqlalchemy as sa


revision = "20261001_0016"
down_revision = "20261001_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("daily_vocabulary_attempts"):
        op.create_table(
        "daily_vocabulary_attempts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("word_id", sa.String(60), nullable=False),
        sa.Column("selected_option", sa.String(1), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "practice_date", "word_id", name="uq_daily_vocab_user_date_word"),
        )
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("daily_vocabulary_attempts")}
    for name, column in (
        ("ix_daily_vocabulary_attempts_user_id", "user_id"),
        ("ix_daily_vocabulary_attempts_practice_date", "practice_date"),
    ):
        if name not in existing_indexes:
            op.create_index(name, "daily_vocabulary_attempts", [column])


def downgrade() -> None:
    op.drop_index("ix_daily_vocabulary_attempts_practice_date", table_name="daily_vocabulary_attempts")
    op.drop_index("ix_daily_vocabulary_attempts_user_id", table_name="daily_vocabulary_attempts")
    op.drop_table("daily_vocabulary_attempts")
