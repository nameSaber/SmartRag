"""initial schema

Revision ID: 20260622_0001
Revises:
Create Date: 2026-06-22
"""

from alembic import op

from app.core.database import Base
from app.models import admin, chat, document, user  # noqa: F401

revision = "20260622_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 使用项目模型作为单一数据结构来源，避免首个迁移脚本与模型定义漂移。
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # 生产环境不提供自动删表降级，避免误操作造成业务数据丢失。
    pass

