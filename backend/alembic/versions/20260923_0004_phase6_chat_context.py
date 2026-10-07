"""Add Phase 6 chat concept context to existing databases."""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0004"
down_revision = "20260923_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "current_concept_id" not in {column["name"] for column in inspector.get_columns("chat_sessions")}:
        op.add_column("chat_sessions", sa.Column("current_concept_id", sa.UUID(), nullable=True))
    if not any(index["name"] == "ix_chat_sessions_current_concept_id" for index in inspector.get_indexes("chat_sessions")):
        op.create_index("ix_chat_sessions_current_concept_id", "chat_sessions", ["current_concept_id"])
    if not any(foreign_key.get("name") == "fk_chat_sessions_current_concept_id_concepts" for foreign_key in inspector.get_foreign_keys("chat_sessions")):
        op.create_foreign_key("fk_chat_sessions_current_concept_id_concepts", "chat_sessions", "concepts", ["current_concept_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_current_concept_id", table_name="chat_sessions")
    op.drop_constraint(
        "fk_chat_sessions_current_concept_id_concepts",
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_column("chat_sessions", "current_concept_id")
