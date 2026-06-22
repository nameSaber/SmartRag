from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


def fail(code: int, message: str, data: Any = None) -> JSONResponse:
    return JSONResponse(status_code=200, content={"code": code, "message": message, "data": data})

