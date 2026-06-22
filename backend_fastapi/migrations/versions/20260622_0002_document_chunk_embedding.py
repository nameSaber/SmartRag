"""add document chunk embedding

Revision ID: 20260622_0002
Revises: 20260622_0001
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260622_0002"
down_revision = "20260622_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("document_chunks")}
    if "embedding_json" in columns:
        return
    op.add_column("document_chunks", sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    # 生产环境不自动删除列，避免误操作造成向量数据丢失。
    pass
