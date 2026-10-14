"""Единый формат ошибок API: {"status": "fail", "message": "..."} + правильный HTTP-код."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def fail(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"status": "fail", "message": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return fail(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Неверный тип id, лишние/недостающие поля, значения вне диапазона → 400 Bad Request
        parts = []
        for err in exc.errors():
            where = ".".join(str(x) for x in err["loc"] if x not in ("body", "query", "path", "form"))
            parts.append(f"{where}: {err['msg']}" if where else err["msg"])
        return fail(400, "; ".join(parts))
