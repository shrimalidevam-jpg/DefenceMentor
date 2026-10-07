"""Mark Phase 3 authentication API baseline.

The Phase 2 schema already includes identity, profile, role, and admin tables.
This revision records the API-layer authentication milestone without changing data.
"""

revision = "20260923_0002"
down_revision = "20260923_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
