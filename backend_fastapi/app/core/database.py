from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
if settings.database_url == "sqlite:///:memory:":
    # 测试环境使用同一个内存连接，避免 SQLite 内存库在多连接下丢表。
    engine_kwargs["poolclass"] = StaticPool
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_schema() -> None:
    # 导入模型模块，确保 SQLAlchemy metadata 能收集到所有表。
    from app.models import user  # noqa: F401
    from app.models import document  # noqa: F401
    from app.models import chat  # noqa: F401
    from app.models import admin  # noqa: F401

    Base.metadata.create_all(bind=engine)
