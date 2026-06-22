from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RateLimitConfig(Base):
    __tablename__ = "rate_limit_configs"

    config_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    single_max: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    single_window_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    minute_max: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    minute_window_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    day_max: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    day_window_seconds: Mapped[int] = mapped_column(Integer, default=86400, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ModelProviderConfig(Base):
    __tablename__ = "model_provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_style: Mapped[str] = mapped_column(String(64), default="openai", nullable=False)
    api_base_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, default="", nullable=False)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RechargePackage(Base):
    __tablename__ = "recharge_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    package_price: Mapped[int] = mapped_column(Integer, nullable=False)
    package_desc: Mapped[str] = mapped_column(Text, default="", nullable=False)
    package_benefit: Mapped[str] = mapped_column(Text, default="", nullable=False)
    llm_token: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_token: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RechargeOrder(Base):
    __tablename__ = "recharge_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    package_id: Mapped[int] = mapped_column(ForeignKey("recharge_packages.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_token: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_token: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wx_transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="NOT_PAY", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pay_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
