from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Query, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.month import Month
from models.month_like import MonthLike
from models.user import User  # noqa: F401 — нужен, чтобы ORM знала таблицу users для ForeignKey

router = APIRouter()

templates = Jinja2Templates(directory="templates")

# Авторизации пока нет: все действия выполняет тестовый пользователь ivan_sadovod (id = 1)
CURRENT_USER_ID = 1


async def find_draft(db: AsyncSession) -> Month | None:
    """Черновик текущего пользователя (по ограничению в БД он максимум один)."""
    stmt = select(Month).where(
        Month.creator_id == CURRENT_USER_ID,
        Month.status == "draft",
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def file_name_or_none(file_name: str) -> str | None:
    """Файлы в ЛР2 на сервер не передаются: форма присылает только имя файла,
    его и пишем в БД как неверный URL (по нему ничего не откроется)."""
    file_name = file_name.strip()
    return file_name or None


# ---------- GET ----------

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


# 2. Новый месяц: черновик текущего пользователя из БД; если его нет — форма первого шага
@router.get("/months/draft")
async def get_months_draft(request: Request, db: AsyncSession = Depends(get_db)):
    draft = await find_draft(db)

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


# ---------- POST ----------

# 4. «Далее»: создать черновик через ORM (название + фото + видео)
@router.post("/months/draft")
async def create_month_draft(
    title: str = Form(""),
    photo: str = Form(""),
    video: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    title = title.strip()
    # Пустое название или черновик уже есть (у пользователя он может быть только один)
    if title == "" or await find_draft(db) is not None:
        return RedirectResponse(url="/months/draft", status_code=303)

    draft = Month(
        title=title,
        image_url=file_name_or_none(photo),
        video_url=file_name_or_none(video),
        status="draft",
        creator_id=CURRENT_USER_ID,
    )
    db.add(draft)
    await db.commit()

    return RedirectResponse(url="/months/draft", status_code=303)


# 5. «Опубликовать»: краткое описание + оба поля по теме, смена статуса через ORM
@router.post("/months/draft/publish")
async def publish_month_draft(
    description: str = Form(...),
    norm_temp: int = Form(...),
    norm_precip: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    draft = await find_draft(db)
    if draft is None:
        return RedirectResponse(url="/months/draft", status_code=303)

    # Меняем атрибуты объекта — ORM сама сформирует UPDATE при commit
    draft.description = description.strip()
    draft.norm_temp = norm_temp
    draft.norm_precip = norm_precip
    draft.status = "published"
    draft.formed_at = datetime.now()
    await db.commit()

    return RedirectResponse(url=f"/months/feed/{draft.id}", status_code=303)


# 6. Удаление с плитки: НЕ через ORM, а сырым SQL UPDATE через курсор (мягкое удаление)
@router.post("/months/{month_id}/delete")
async def delete_month(
    month_id: int,
    temp_from: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    update_query = """
        UPDATE months
        SET status = 'deleted'
        WHERE id = :id
    """
    await db.execute(text(update_query), {"id": month_id})
    await db.commit()

    # Возвращаемся на плитку с тем же фильтром температуры
    url = f"/months?temp_from={temp_from}" if temp_from else "/months"
    return RedirectResponse(url=url, status_code=303)
