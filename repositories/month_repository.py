"""Доступ к таблицам months и month_likes через ORM (SQLAlchemy).

Здесь только запросы к БД: никаких HTTP-кодов и JSON — это забота обработчиков в api/.
Удалённые месяцы (status='deleted') отсюда наружу не выходят.
"""
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.month import Month
from models.month_like import MonthLike


def likes_count_col():
    return func.count(MonthLike.id).label("likes_count")


def is_liked_col(user_id: int):
    """1, если среди лайков месяца (они уже присоединены LEFT JOIN) есть лайк текущего пользователя.
    Считаем агрегатом по той же группе: MAX(CASE WHEN month_likes.user_id = :uid THEN 1 ELSE 0 END)."""
    return func.max(case((MonthLike.user_id == user_id, 1), else_=0)).label("is_liked")


async def list_published(db: AsyncSession, user_id: int, temp_from: int | None, title: str | None):
    """Опубликованные месяцы + число лайков + признак «мой» (0/1). Фильтры — на стороне БД."""
    is_mine = case((Month.creator_id == user_id, 1), else_=0).label("is_mine")
    stmt = (
        select(Month, likes_count_col(), is_mine)
        .outerjoin(MonthLike, Month.id == MonthLike.month_id)
        .where(Month.status == "published")
        .group_by(Month.id)
        .order_by(Month.id)
    )
    if temp_from is not None:
        stmt = stmt.where(Month.norm_temp >= temp_from)
    if title:
        stmt = stmt.where(Month.title.ilike(f"%{title}%"))
    return (await db.execute(stmt)).all()


async def get_feed_item(db: AsyncSession, user_id: int, month_id: int | None, next_month: bool):
    """Лента: БД возвращает ровно одну опубликованную запись (или None)."""
    base = (
        select(Month, likes_count_col(), is_liked_col(user_id))
        .outerjoin(MonthLike, Month.id == MonthLike.month_id)
        .where(Month.status == "published")
        .group_by(Month.id)
    )
    first_stmt = base.order_by(Month.id).limit(1)
    if month_id is None:
        stmt = first_stmt
    elif next_month:
        stmt = base.where(Month.id > month_id).order_by(Month.id).limit(1)
    else:
        stmt = base.where(Month.id == month_id)

    row = (await db.execute(stmt)).first()
    if row is None and next_month:  # был последний — по кругу на первый
        row = (await db.execute(first_stmt)).first()
    return row


async def get_draft(db: AsyncSession, user_id: int) -> Month | None:
    stmt = select(Month).where(Month.creator_id == user_id, Month.status == "draft")
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_not_deleted(db: AsyncSession, month_id: int) -> Month | None:
    stmt = select(Month).where(Month.id == month_id, Month.status != "deleted")
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_draft(db: AsyncSession, user_id: int, title: str,
                       image_url: str, video_url: str) -> Month:
    month = Month(title=title, image_url=image_url, video_url=video_url,
                  status="draft", creator_id=user_id)
    db.add(month)
    await db.commit()
    await db.refresh(month)  # подтянуть created_at, который поставила БД
    return month


async def publish(db: AsyncSession, month: Month, fields: dict) -> Month:
    for name, value in fields.items():
        setattr(month, name, value)
    month.status = "published"
    month.formed_at = datetime.now()
    await db.commit()
    await db.refresh(month)
    return month


async def soft_delete(db: AsyncSession, month: Month) -> None:
    month.status = "deleted"
    await db.commit()


async def set_like(db: AsyncSession, user_id: int, month_id: int, value: int) -> tuple[int, int]:
    """value=1 — поставить лайк (если его ещё нет), value=0 — снять. Возвращает (is_liked, likes_count)."""
    stmt = select(MonthLike).where(MonthLike.user_id == user_id, MonthLike.month_id == month_id)
    like = (await db.execute(stmt)).scalar_one_or_none()
    if value == 1 and like is None:
        db.add(MonthLike(user_id=user_id, month_id=month_id))
    elif value == 0 and like is not None:
        await db.delete(like)
    await db.commit()

    count_stmt = select(func.count(MonthLike.id)).where(MonthLike.month_id == month_id)
    likes_count = (await db.execute(count_stmt)).scalar_one()
    return value, likes_count
