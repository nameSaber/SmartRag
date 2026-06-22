from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.api.v1.chat import ws_router
from app.core.config import settings
from app.core.database import create_schema
from app.core.exceptions import register_exception_handlers
from app.core.responses import ok


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 测试和本地快速启动可以自动建表；Docker/生产环境应通过 Alembic 迁移建表。
    if settings.auto_create_schema:
        create_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/health")
    def health_check():
        return ok({"status": "UP"})

    return app


app = create_app()
