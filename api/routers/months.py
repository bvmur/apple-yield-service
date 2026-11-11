from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Form, File, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.month import Month
from models.user import User
from services.storage import upload

from models.month_like import MonthLike
from schemas.month import MonthListItem, MonthFeedItem, MonthDraft, MonthPublish, MonthLikeIn, MonthLikeResult
from core.deps import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/months", tags=["months"])

async def find_draft(db: AsyncSession, user: User) -> Month | None:
    stmt = select(Month).where(
        Month.creator_id == user.id,
        Month.status == "draft",
    )
    return (await db.execute(stmt)).scalar_one_or_none()


@router.get(
    "",
    response_model=list[MonthListItem],
    summary="Список месяцев",
    description="Опубликованные месяцы с числом лайков. Фильтр temp_from — норма температуры не ниже "
                "заданной. Доступно без входа; is_mine = 1, если месяц создал текущий пользователь.",
)
async def get_months_list(temp_from: str = Query("", description="Температура от, °C (необязательно)"),
                          db: AsyncSession = Depends(get_db),
                          user: User | None = Depends(get_current_user_optional)):
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
    response = []
    for month, likes in months:
        response.append({
            "id": month.id,
            "title": month.title,
            "norm_temp": month.norm_temp,
            "norm_precip": month.norm_precip,
            "image_url": month.image_url,
            "likes_count": likes,
            "is_mine": 1 if user is not None and month.creator_id == user.id else 0,
        })
        
    return response


@router.get(
    "/feed/{month_id}",
    response_model=MonthFeedItem,
    summary="Лента: месяц по id или следующий",
    description="Без next — месяц с этим id. С next=true — следующий опубликованный после него, "
                "после последнего снова первый. Доступно без входа.",
    responses={404: {"description": "Месяц не найден"}},
)
@router.get(
    "/feed",
    response_model=MonthFeedItem,
    summary="Лента: первый месяц",
    description="Первый опубликованный месяц — начало ленты. Доступно без входа; "
                "is_liked = 1, если текущий пользователь лайкнул месяц.",
)
async def get_months_feed(month_id: int | None = None,
                          next_month: bool = Query(default=False, alias="next"),
                            db: AsyncSession = Depends(get_db),
                            user: User | None = Depends(get_current_user_optional),
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
    
    # Гость лайков не ставит — у него is_liked всегда 0
    liked = 0
    if user is not None:
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
    
@router.get(
    "/draft",
    response_model=MonthDraft,
    summary="Черновик",
    description="Черновик текущего пользователя (не больше одного), id не указывается. Требуется вход.",
    responses={401: {"description": "Требуется вход"}, 404: {"description": "Черновика нет"}},
)
async def get_month_draft(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    draft = await find_draft(db, user)
    if draft is None:
        raise HTTPException(status_code=404, detail="Черновика нет")
    return draft


@router.post(
    "",
    response_model=MonthDraft,
    status_code=201,
    summary="Создать месяц (черновик)",
    description="Название, фото и видео в multipart/form-data. Файлы сохраняются в MinIO "
                "под сгенерированными латинскими именами, создатель — текущий пользователь. Требуется вход.",
    responses={
        400: {"description": "Пустое название или неверный тип файла"},
        401: {"description": "Требуется вход"},
        409: {"description": "Черновик уже есть"},
    },
)
async def create_month(
    title: str = Form(...),
    photo: UploadFile = File(...),
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    
    title = title.strip()
    
    if await find_draft(db, user) is not None:
        raise HTTPException(status_code=409, detail="Черновик уже существует")
    
    if title == "" or len(title) > 30:
        raise HTTPException(status_code=400, detail="Название: от 1 до 30 символов")
    
    image_name = await upload(photo, "image")
    video_name = await upload(video, "video")
    
    draft = Month(
        title=title,
        image_url=image_name,
        video_url=video_name,
        status="draft",
        creator_id=user.id,
    )
    
    db.add(draft)
    await db.commit()
    return draft

@router.put(
    "/draft/publish",
    response_model=MonthDraft,
    summary="Опубликовать черновик",
    description="Заполняет описание, температуру и осадки черновика и меняет статус на published. "
                "Требуется вход.",
    responses={
        400: {"description": "Описание пустое"},
        401: {"description": "Требуется вход"},
        404: {"description": "Черновика нет"},
    },
)
async def publish_month(
    data: MonthPublish,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    
    draft = await find_draft(db, user)
    if draft is None:
        raise HTTPException(status_code=404, detail="Черновик не найден")
    
    description = data.description.strip()
    if description == "":
        raise HTTPException(status_code=400, detail="Описание не может быть пустым")

    draft.description = description
    draft.norm_temp = data.norm_temp
    draft.norm_precip = data.norm_precip
    draft.status = "published"
    draft.formed_at = datetime.now()
    await db.commit()

    return draft


@router.delete(
    "/{month_id}",
    status_code=204,
    summary="Удалить месяц",
    description="Мягкое удаление: статус меняется на deleted. Удалить можно только свой месяц. Требуется вход.",
    responses={
        401: {"description": "Требуется вход"},
        403: {"description": "Чужой месяц"},
        404: {"description": "Месяц не найден"},
    },
)
async def delete_month(
    month_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    month = await db.get(Month, month_id)
    if month is None or month.status == "deleted":
        raise HTTPException(status_code=404, detail="Месяц не найден")

    # Удалять можно только свои месяцы
    if month.creator_id != user.id:
        raise HTTPException(status_code=403, detail="Можно удалить только свой месяц")

    # Мягкое удаление: строка остаётся, меняется только статус
    month.status = "deleted"
    await db.commit()


@router.post(
    "/{month_id}/like",
    response_model=MonthLikeResult,
    summary="Лайк",
    description="value = 1 ставит лайк от текущего пользователя, value = 0 снимает. "
                "Только для опубликованных месяцев. Требуется вход.",
    responses={401: {"description": "Требуется вход"}, 404: {"description": "Месяц не найден"}},
)
async def like_month(
    month_id: int,
    data: MonthLikeIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    month = await db.get(Month, month_id)
    if month is None or month.status != "published":
        raise HTTPException(status_code=404, detail="Месяц не найден")

    like = await db.scalar(
        select(MonthLike).where(
            MonthLike.month_id == month_id,
            MonthLike.user_id == user.id,
        )
    )

    if data.value == 1 and like is None:
        db.add(MonthLike(user_id=user.id, month_id=month_id))
    elif data.value == 0 and like is not None:
        await db.delete(like)
    await db.commit()

    likes = await db.scalar(
        select(func.count(MonthLike.id)).where(MonthLike.month_id == month_id)
    )

    return {
        "month_id": month_id,
        "likes_count": likes,
        "is_liked": data.value,
    }
