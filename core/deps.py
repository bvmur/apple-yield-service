from fastapi import Cookie, Depends, HTTPException, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.user import User
from services.session import COOKIE_NAME, get_user_id

# Схема авторизации «по куке session_id». Нужна FastAPI, чтобы прочитать куку,
# и Swagger, чтобы нарисовать замок и кнопку Authorize у методов создателя.
cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)


async def find_user_by_session(session_id: str | None, db: AsyncSession) -> User | None:
    """Кука → Redis → пользователь. Нет куки или сессия истекла → None."""
    if session_id is None:
        return None

    user_id = await get_user_id(session_id)
    if user_id is None:
        return None

    return await db.get(User, user_id)


async def get_current_user_optional(
    session_id: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Пользователь, если вошёл, иначе None (гость). Для методов чтения — без замка в Swagger."""
    return await find_user_by_session(session_id, db)


async def get_current_user(
    session_id: str | None = Security(cookie_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Функция-singleton: текущий пользователь. Без входа — 401. Для методов создателя — с замком."""
    user = await find_user_by_session(session_id, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется вход")
    return user
