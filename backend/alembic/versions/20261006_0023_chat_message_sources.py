"""Persist verified document links on tutor chat messages."""

from alembic import op
import sqlalchemy as sa


revision = "20261006_0023"
down_revision = "20261006_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "sources" not in columns:
        op.add_column(
            "chat_messages",
            sa.Column("sources", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )


def downgrade() -> None:
    op.drop_column("chat_messages", "sources")
