from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.user import User
from services.session import COOKIE_NAME, get_user_id

cookie_scheme = APIKeyCookie(name=COOKIE_NAME, auto_error=False)


async def get_current_user_optional(
    session_id: str | None = Security(cookie_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:

    if session_id is None:
        return None

    user_id = await get_user_id(session_id)
    if user_id is None:
        return None

    return await db.get(User, user_id)


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Функция-singleton: текущий пользователь. Без входа — 401."""
    if user is None:
        raise HTTPException(status_code=401, detail="Требуется вход")
    return user
