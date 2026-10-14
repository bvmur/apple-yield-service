from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.templating import Jinja2Templates
from data.collections import months_db
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


from db.session import get_db
from models.month import Month
from models.month_like import MonthLike

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# 1. Плитка: список опубликованных месяцев + фильтр по температуре
@router.get("/")
@router.get("/months")
async def get_months_list(request: Request,
                          temp_from: str = "",
                          db: AsyncSession = Depends(get_db)):
    temp = None
    if temp_from != "":
        try:
            temp = int(temp_from)
        except ValueError:
            temp = None

    likes_count = func.count(MonthLike.id).label("likes_count")
    stmt = (
        select(Month, likes_count)
        .outerjoin(MonthLike, Month.id == MonthLike.month_id)
        .where(Month.status == "published")
        .group_by(Month.id)
        .order_by(Month.id)
    )
    
    if temp is not None:
        stmt = stmt.where(Month.norm_temp >= temp)
        
    result = await db.execute(stmt)
    months = result.all()
    return templates.TemplateResponse(
        request=request,
        name="months_list.html",
        context={"months": months, "temp": temp, "active_tab": "list"},
    )


# 2. Новый месяц: один черновик (status == "draft"), если его нет — пустая форма
@router.get("/months/draft")
def get_months_draft(request: Request):
    draft = next((month for month in months_db if month["status"] == "draft"), None)

    return templates.TemplateResponse(
        request=request,
        name="months_draft.html",
        context={"draft": draft, "active_tab": "draft"},
    )


# 3. Лента: без id — первый месяц, с id — этот месяц, ?next=true — следующий по кругу.
#    Нужный месяц выбирает сама БД: каждый запрос возвращает ровно одну строку.
@router.get("/months/feed")
@router.get("/months/feed/{month_id}")
async def get_months_feed(
    request: Request,
    month_id: int | None = None,
    next_month: bool = Query(default=False, alias="next"),
    db: AsyncSession = Depends(get_db),
):
    likes_count = func.count(MonthLike.id).label("likes_count")
    base = (
        select(Month, likes_count)
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

    # Дошли до последнего опубликованного — начинаем ленту сначала
    if row is None and next_month:
        row = (await db.execute(first_stmt)).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Месяц не найден.")

    month, likes = row
    return templates.TemplateResponse(
        request=request,
        name="months_feed.html",
        context={"month": month, "likes_count": likes, "active_tab": "feed"},
    )
