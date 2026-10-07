"""Add verified dynamic tutorial resources for grades 5 through 12."""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0012"
down_revision = "20260925_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("tutorial_resources"):
        op.create_table(
            "tutorial_resources",
            sa.Column("board", sa.String(40), nullable=False),
            sa.Column("grade_level", sa.Integer(), nullable=False),
            sa.Column("subject", sa.String(120), nullable=False),
            sa.Column("topic", sa.String(180), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("url", sa.String(2048), nullable=False),
            sa.Column("provider", sa.String(120), nullable=False),
            sa.Column("resource_type", sa.String(40), nullable=False, server_default="video"),
            sa.Column("language", sa.String(40), nullable=False, server_default="English"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_by", sa.Uuid(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["verified_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("url"),
        )
        inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("tutorial_resources")}
    for name, columns in (
        ("ix_tutorial_resources_board", ["board"]),
        ("ix_tutorial_resources_grade_level", ["grade_level"]),
        ("ix_tutorial_resources_subject", ["subject"]),
        ("ix_tutorial_resources_topic", ["topic"]),
        ("ix_tutorial_resources_is_verified", ["is_verified"]),
        ("ix_tutorial_resources_is_published", ["is_published"]),
    ):
        if name not in existing_indexes:
            op.create_index(name, "tutorial_resources", columns)


def downgrade() -> None:
    op.drop_index("ix_tutorial_resources_is_published", table_name="tutorial_resources")
    op.drop_index("ix_tutorial_resources_is_verified", table_name="tutorial_resources")
    op.drop_index("ix_tutorial_resources_topic", table_name="tutorial_resources")
    op.drop_index("ix_tutorial_resources_subject", table_name="tutorial_resources")
    op.drop_index("ix_tutorial_resources_grade_level", table_name="tutorial_resources")
    op.drop_index("ix_tutorial_resources_board", table_name="tutorial_resources")
    op.drop_table("tutorial_resources")
