from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user
from core.security import hash_password
from db.session import get_db
from models.user import User
from schemas.user import UserOut, UserRegister

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


@router.post("/login", response_model=UserOut)
async def login(user: User = Depends(get_current_user)):
    """Заглушка до ЛР4: всегда «входит» текущий пользователь из функции-singleton."""
    return user


@router.post("/logout", status_code=204)
async def logout():
    """Заглушка до ЛР4: сессий и токенов пока нет, выходить не из чего."""
    return None