import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")

    # 配置在模块导入时缓存，测试中重载相关模块可保持数据库隔离。
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.services.rate_limiter import reset_in_memory_rate_limiter

    reset_in_memory_rate_limiter()
    from app.core.database import Base, create_schema, engine

    create_schema()
    Base.metadata.drop_all(bind=engine)
    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
