from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from data.collections import months_db

router = APIRouter()

templates = Jinja2Templates(directory="templates")


# 1. Плитка: список опубликованных месяцев + фильтр по температуре
@router.get("/")
@router.get("/months")
def get_months_list(request: Request, temp_from: str = ""):
    temp = None
    if temp_from != "":
        try:
            temp = int(temp_from)
        except ValueError:
            temp = None

    months = [
        {**month, "likes_count": len(month["likes"])}
        for month in months_db
        if month["status"] == "published" and (temp is None or month["norm_temp"] >= temp)
    ]

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


# 3. Лента: без id — первый месяц, с id — этот месяц, ?next=true — следующий по кругу
@router.get("/months/feed")
@router.get("/months/feed/{month_id}")
def get_months_feed(
    request: Request,
    month_id: int | None = None,
    next_month: bool = Query(default=False, alias="next"),
):
    published = [month for month in months_db if month["status"] == "published"]

    index: int | None
    if month_id is None:
        index = 0
    else:
        index = next((i for i, m in enumerate(published) if m["id"] == month_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="Месяц не найден.")

    if next_month:
        index = (index + 1) % len(published)

    month = published[index]
    month = {**month, "likes_count": len(month["likes"])}

    return templates.TemplateResponse(
        request=request,
        name="months_feed.html",
        context={"month": month, "active_tab": "feed"},
    )
