from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    # Храним не пароль, а его хэш. У пользователей из seed.sql пароля нет — пустая строка
    password_hash: Mapped[str] = mapped_column(String(255), server_default="")
    is_moderator: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    