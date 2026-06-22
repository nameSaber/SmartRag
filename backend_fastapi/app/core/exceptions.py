from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class BizError(Exception):
    def __init__(self, message: str, code: int = 400, data=None):
        self.message = message
        self.code = code
        self.data = data


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def biz_error_handler(_: Request, exc: BizError):
        return JSONResponse(status_code=200, content={"code": exc.code, "message": exc.message, "data": exc.data})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=200, content={"code": 422, "message": str(exc.errors()[0]["msg"]), "data": None})

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=200, content={"code": exc.status_code, "message": str(exc.detail), "data": None})

