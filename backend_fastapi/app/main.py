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
    # 早期开发阶段直接建表，后续接入 Alembic 后迁移到版本化脚本。
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
