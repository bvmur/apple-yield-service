from fastapi import APIRouter, Depends, HTTPException, Response, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.deps import cookie_scheme
from core.security import hash_password, verify_password
from db.session import get_db
from models.user import User
from schemas.user import UserLogin, UserOut, UserRegister
from services.session import COOKIE_NAME, create_session, delete_session

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    username = data.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Логин: от 3 до 30 символов")

    existing_user = await db.execute(select(User).where(User.username == username))
    if existing_user.scalar():
        raise HTTPException(status_code=409, detail="Логин уже занят")

    new_user = User(username=username, password=hash_password(data.password))

    db.add(new_user)
    await db.commit()

    return new_user


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    session_id: str | None = Security(cookie_scheme),
):
    """Деавторизация: удалить сессию из Redis и стереть куку."""
    if session_id is not None:
        await delete_session(session_id)
    response.delete_cookie(COOKIE_NAME)


@router.post("/login", response_model=UserOut)
async def login(
    data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Аутентификация: проверить логин и пароль, создать сессию в Redis и поставить куку."""
    user = await db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    session_id = await create_session(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        max_age=settings.SESSION_TTL,
        samesite="lax",
    )
    return user
