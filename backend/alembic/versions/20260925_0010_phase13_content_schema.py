"""Align legacy content tables with the Phase 13 content models."""

from alembic import op
import sqlalchemy as sa


revision = "20260925_0010"
down_revision = "20260924_0009"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    source_columns = _columns("sources")
    if "url" not in source_columns:
        op.add_column("sources", sa.Column("url", sa.String(2048), nullable=True))
    if "is_verified" not in source_columns:
        op.add_column("sources", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "published_on" not in source_columns:
        op.add_column("sources", sa.Column("published_on", sa.Date(), nullable=True))

    document_columns = _columns("content_documents")
    if "storage_path" not in document_columns:
        op.add_column("content_documents", sa.Column("storage_path", sa.String(1024), nullable=True))
    if "content_hash" not in document_columns:
        op.add_column("content_documents", sa.Column("content_hash", sa.String(128), nullable=True))

    chunk_columns = _columns("content_chunks")
    if "document_id" not in chunk_columns and "content_document_id" in chunk_columns:
        op.alter_column("content_chunks", "content_document_id", new_column_name="document_id")
    elif "document_id" not in chunk_columns:
        op.add_column("content_chunks", sa.Column("document_id", sa.Uuid(), nullable=True))
    if "page_reference" not in chunk_columns and "section_reference" in chunk_columns:
        op.alter_column("content_chunks", "section_reference", new_column_name="page_reference")
    elif "page_reference" not in chunk_columns:
        op.add_column("content_chunks", sa.Column("page_reference", sa.String(100), nullable=True))
    if "topic_id" not in chunk_columns:
        op.add_column("content_chunks", sa.Column("topic_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    chunk_columns = _columns("content_chunks")
    if "topic_id" in chunk_columns:
        op.drop_column("content_chunks", "topic_id")
    if "page_reference" in chunk_columns:
        op.alter_column("content_chunks", "page_reference", new_column_name="section_reference")
    if "document_id" in chunk_columns:
        op.alter_column("content_chunks", "document_id", new_column_name="content_document_id")

    document_columns = _columns("content_documents")
    if "content_hash" in document_columns:
        op.drop_column("content_documents", "content_hash")
    if "storage_path" in document_columns:
        op.drop_column("content_documents", "storage_path")

    source_columns = _columns("sources")
    if "published_on" in source_columns:
        op.drop_column("sources", "published_on")
    if "is_verified" in source_columns:
        op.drop_column("sources", "is_verified")
    if "url" in source_columns:
        op.drop_column("sources", "url")
