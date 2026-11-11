import secrets

from redis.asyncio import Redis

from core.config import settings

# Один клиент Redis на всё приложение — как клиент MinIO в storage.py
redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,   # получать строки, а не байты
)

COOKIE_NAME = "session_id"
PREFIX = "session:"


async def create_session(user_id: int) -> str:
    """Создать сессию: случайный ключ → id пользователя, со сроком жизни. Вернуть ключ."""
    session_id = secrets.token_urlsafe(32)
    await redis.set(PREFIX + session_id, user_id, ex=settings.SESSION_TTL)
    return session_id


async def get_user_id(session_id: str) -> int | None:
    """По ключу из куки узнать id пользователя. Сессии нет или истекла → None."""
    value = await redis.get(PREFIX + session_id)
    return int(value) if value is not None else None


async def delete_session(session_id: str) -> None:
    """Удалить сессию — это и есть выход."""
    await redis.delete(PREFIX + session_id)