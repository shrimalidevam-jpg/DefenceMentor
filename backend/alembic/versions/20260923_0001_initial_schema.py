"""Create the Phase 2 initial NDA Chatbot schema."""
from alembic import op
from app.models import *  # noqa: F403
from app.models.base import Base

revision = "20260923_0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
