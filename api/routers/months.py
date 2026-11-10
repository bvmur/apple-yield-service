from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.month import Month
from models.user import User

from models.month_like import MonthLike
from schemas.month import MonthListItem, MonthFeedItem
from core.deps import get_current_user

router = APIRouter(prefix="/api/months", tags=["months"])


@router.get("", response_model=list[MonthListItem])
async def get_months_list(temp_from: str = "",
                          db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    temp = None
    
    if temp_from != "":
        try:
            temp = int(temp_from)
        except ValueError:
            temp = None  # Игнорируем некорректное значение фильтра
    
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
    response = []
    
    for month, likes in months:
        response.append({
            "id": month.id,
            "title": month.title,
            "norm_temp": month.norm_temp,
            "norm_precip": month.norm_precip,
            "image_url": month.image_url,
            "likes_count": likes,
            "is_mine": 1 if month.creator_id == user.id else 0,
        })
        
    return response


@router.get("/feed", response_model=MonthFeedItem)
@router.get("/feed/{month_id}", response_model=MonthFeedItem)
async def get_months_feed(month_id: int | None = None,
                          next_month: bool = Query(default=False, alias="next"),
                            db: AsyncSession = Depends(get_db),
                            user: User = Depends(get_current_user),
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
    
    liked = await db.scalar(
        select(func.count(MonthLike.id)).where(
            MonthLike.month_id == month.id,
            MonthLike.user_id == user.id
        )
    )

    return{
        "id": month.id,
        "title": month.title,
        "norm_temp": month.norm_temp,
        "norm_precip": month.norm_precip,
        "description": month.description,
        "image_url": month.image_url,
        "video_url": month.video_url,
        "likes_count": likes,
        "is_liked": 1 if liked else 0,
    }
    