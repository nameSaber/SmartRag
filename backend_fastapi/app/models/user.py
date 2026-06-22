from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="USER", nullable=False)
    primary_org: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_token_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_token_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    org_tags: Mapped[list["UserOrgTag"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class OrgTag(Base):
    __tablename__ = "org_tags"

    tag_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    parent_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_max_size_bytes: Mapped[int] = mapped_column(Integer, default=104857600, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserOrgTag(Base):
    __tablename__ = "user_org_tags"
    __table_args__ = (UniqueConstraint("user_id", "tag_id", name="uk_user_org_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tag_id: Mapped[str] = mapped_column(ForeignKey("org_tags.tag_id"), nullable=False)
    user: Mapped[User] = relationship(back_populates="org_tags")


class UserTokenRecord(Base):
    __tablename__ = "user_token_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    token_type: Mapped[str] = mapped_column(String(16), nullable=False)
    change_type: Mapped[str] = mapped_column(String(16), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserDailyChatCount(Base):
    __tablename__ = "user_daily_chat_count"
    __table_args__ = (UniqueConstraint("user_id", "record_date", name="uk_user_daily_chat_count"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    chat_request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

