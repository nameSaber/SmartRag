"""add audit logs

Revision ID: 20260622_0003
Revises: 20260622_0002
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260622_0003"
down_revision = "20260622_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "audit_logs" in tables:
        return
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )


def downgrade() -> None:
    # 审计日志不自动降级删除。
    pass

