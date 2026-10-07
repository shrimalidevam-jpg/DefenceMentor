"""Support separate 15-mark daily and tomorrow revision exam attempts."""

from alembic import op
import sqlalchemy as sa


revision = "20261006_0021"
down_revision = "20261006_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("daily_review_attempts")}
    if "attempt_no" not in columns:
        op.add_column("daily_review_attempts", sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"))
    connection = op.get_bind()
    constraints = sa.inspect(connection).get_unique_constraints("daily_review_attempts")
    for constraint in constraints:
        if set(constraint.get("column_names") or []) == {"user_id", "plan_date"}:
            op.drop_constraint(constraint["name"], "daily_review_attempts", type_="unique")
    constraints = sa.inspect(connection).get_unique_constraints("daily_review_attempts")
    if not any(
        set(constraint.get("column_names") or []) == {"user_id", "plan_date", "attempt_no"}
        for constraint in constraints
    ):
        op.create_unique_constraint(
            "uq_daily_review_attempt_user_date_number",
            "daily_review_attempts",
            ["user_id", "plan_date", "attempt_no"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_daily_review_attempt_user_date_number", "daily_review_attempts", type_="unique")
    op.create_unique_constraint(
        "uq_daily_review_attempt_user_plan_date",
        "daily_review_attempts",
        ["user_id", "plan_date"],
    )
    op.drop_column("daily_review_attempts", "attempt_no")
