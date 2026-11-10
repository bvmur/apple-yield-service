from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.user import User

# Заглушка до ЛР4: в этой лабораторной создатель зафиксирован
CURRENT_USER_ID = 1


async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Функция-singleton: единственная точка получения текущего пользователя."""
    user = await db.get(User, CURRENT_USER_ID)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user