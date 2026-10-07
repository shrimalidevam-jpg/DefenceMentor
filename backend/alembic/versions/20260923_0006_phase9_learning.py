"""Add the durable target concept for Phase 9 learning sessions."""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0006"
down_revision = "20260923_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "target_concept_id" not in {column["name"] for column in inspector.get_columns("learning_sessions")}:
        op.add_column("learning_sessions", sa.Column("target_concept_id", sa.Uuid(), nullable=True))
    if not any(index["name"] == "ix_learning_sessions_target_concept_id" for index in inspector.get_indexes("learning_sessions")):
        op.create_index("ix_learning_sessions_target_concept_id", "learning_sessions", ["target_concept_id"])
    if not any(foreign_key.get("name") == "fk_learning_sessions_target_concept_id_concepts" for foreign_key in inspector.get_foreign_keys("learning_sessions")):
        op.create_foreign_key("fk_learning_sessions_target_concept_id_concepts", "learning_sessions", "concepts", ["target_concept_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_learning_sessions_target_concept_id_concepts", "learning_sessions", type_="foreignkey")
    op.drop_index("ix_learning_sessions_target_concept_id", table_name="learning_sessions")
    op.drop_column("learning_sessions", "target_concept_id")