from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Обёртка успешного ответа, как в методичке: {"status": "success", "data": ..., "message": ...}"""
    status: str = "success"
    data: T | None = None
    message: str | None = None
