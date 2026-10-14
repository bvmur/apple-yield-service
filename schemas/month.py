"""Сериализаторы месяцев (услуг).

Выходные схемы (Out) описывают, какие поля уходят клиенту в JSON.
Входные схемы (In) описывают, что клиент имеет право прислать.
Системных полей (id, status, creator_id, created_at, formed_at) во входных схемах нет,
а extra="forbid" отклоняет запрос, если клиент всё же попытается их передать.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MonthListItemOut(BaseModel):
    """Карточка в списке (плитка)."""
    id: int
    title: str
    phase: str | None
    norm_temp: int | None
    norm_precip: int | None
    impact: int | None
    image_url: str | None
    likes_count: int
    is_mine: int = Field(description="1 — создатель месяца совпадает с текущим пользователем, иначе 0")


class MonthFeedOut(BaseModel):
    """Одна запись ленты."""
    id: int
    title: str
    phase: str | None
    description: str | None
    norm_temp: int | None
    norm_precip: int | None
    impact: int | None
    image_url: str | None
    video_url: str | None
    likes_count: int
    is_liked: int = Field(description="1 — текущий пользователь лайкнул месяц, иначе 0")


class MonthOut(BaseModel):
    """Полная информация о месяце (черновик, ответ на создание и публикацию)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    phase: str | None
    description: str | None
    norm_temp: int | None
    norm_precip: int | None
    impact: int | None
    image_url: str | None
    video_url: str | None
    status: str
    created_at: datetime
    formed_at: datetime | None
    creator_id: int


class MonthPublishIn(BaseModel):
    """Тело PUT публикации: краткое описание и оба поля по теме (обязательно), фаза и значимость — по желанию."""
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500)
    norm_temp: int = Field(ge=-50, le=50)
    norm_precip: int = Field(ge=0, le=1000)
    phase: str | None = Field(default=None, max_length=50)
    impact: int | None = Field(default=None, ge=1, le=3)


class LikeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Literal[0, 1] = Field(description="1 — поставить лайк, 0 — отменить")


class LikeOut(BaseModel):
    month_id: int
    is_liked: int
    likes_count: int
