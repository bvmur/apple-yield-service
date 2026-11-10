from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.month import Month
from models.user import User

from models.month_like import MonthLike
from schemas.month import MonthListItem
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