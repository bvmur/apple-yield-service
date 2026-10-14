"""REST API домена «пользователь». Все адреса начинаются с /api/users."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from db.session import get_db
from repositories import user_repository as repo
from schemas.common import ApiResponse
from schemas.user import UserLoginIn, UserOut, UserRegisterIn

router = APIRouter(prefix="/api/users", tags=["users"])


# 8. POST регистрация
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[UserOut])
async def register(body: UserRegisterIn, db: AsyncSession = Depends(get_db)):
    if await repo.get_by_username(db, body.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким логином уже есть")
    user = await repo.create(db, body.username, hash_password(body.password))
    return ApiResponse(data=UserOut.model_validate(user), message="Пользователь зарегистрирован")


# 9. POST аутентификация - заглушка до ЛР4
@router.post("/login", response_model=ApiResponse[None])
async def login(body: UserLoginIn):
    return ApiResponse(message="Заглушка: аутентификация будет реализована в ЛР4")


# 10. POST деавторизация — заглушка до ЛР4
@router.post("/logout", response_model=ApiResponse[None])
async def logout():
    return ApiResponse(message="Заглушка: деавторизация будет реализована в ЛР4")
