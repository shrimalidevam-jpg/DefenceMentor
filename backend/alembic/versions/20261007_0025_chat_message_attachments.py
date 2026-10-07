"""Persist file attachments on chat messages."""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0025"
down_revision = "20261007_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "attachments" not in columns:
        op.add_column(
            "chat_messages",
            sa.Column("attachments", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "attachments" in columns:
        op.drop_column("chat_messages", "attachments")
