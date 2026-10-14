"""Текущий пользователь.

Авторизации пока нет (появится в ЛР4), поэтому пользователь-создатель
зафиксирован константой. Функция-singleton: благодаря lru_cache объект
создаётся один раз и при каждом вызове возвращается тот же самый экземпляр.
Все методы API получают пользователя только через эту функцию:
    user: CurrentUser = Depends(get_current_user)
В ЛР4 достаточно будет заменить тело функции на чтение пользователя из сессии/токена.
"""
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_USER_ID = 1
DEFAULT_USERNAME = "ivan_sadovod"


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str


@lru_cache(maxsize=1)
def get_current_user() -> CurrentUser:
    return CurrentUser(id=DEFAULT_USER_ID, username=DEFAULT_USERNAME)
