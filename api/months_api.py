"""REST API домена «месяцы» (услуги). Все адреса начинаются с /api/months."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.current_user import CurrentUser, get_current_user
from db.session import get_db
from repositories import month_repository as repo
from schemas.common import ApiResponse
from schemas.month import (LikeIn, LikeOut, MonthFeedOut, MonthListItemOut,
                           MonthOut, MonthPublishIn)
from storage import minio_storage

router = APIRouter(prefix="/api/months", tags=["months"])


def _month_fields(month) -> dict:
    return {name: getattr(month, name) for name in (
        "id", "title", "phase", "norm_temp", "norm_precip", "impact", "image_url")}


# 1. GET список с фильтрацией (только опубликованные) + признак is_mine
@router.get("", response_model=ApiResponse[list[MonthListItemOut]])
async def list_months(
    temp_from: int | None = Query(default=None, ge=-50, le=50, description="Температура от, °C"),
    title: str | None = Query(default=None, max_length=30, description="Поиск по названию"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rows = await repo.list_published(db, user.id, temp_from, title)
    data = [MonthListItemOut(**_month_fields(m), likes_count=likes, is_mine=mine)
            for m, likes, mine in rows]
    return ApiResponse(data=data)


# 2. GET лента (только опубликованные) + признак is_liked
@router.get("/feed", response_model=ApiResponse[MonthFeedOut])
@router.get("/feed/{month_id}", response_model=ApiResponse[MonthFeedOut])
async def get_feed(
    month_id: int | None = None,
    next_month: bool = Query(default=False, alias="next"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    row = await repo.get_feed_item(db, user.id, month_id, next_month)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Месяц не найден")
    m, likes, liked = row
    data = MonthFeedOut(**_month_fields(m), description=m.description, video_url=m.video_url,
                        likes_count=likes, is_liked=liked)
    return ApiResponse(data=data)


# 3. GET черновик текущего пользователя (id не указывается)
@router.get("/draft", response_model=ApiResponse[MonthOut])
async def get_draft(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    draft = await repo.get_draft(db, user.id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Черновика нет")
    return ApiResponse(data=MonthOut.model_validate(draft))


# 4. POST создание черновика + загрузка фото и видео файлами в MinIO
@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[MonthOut])
async def create_month(
    title: str = Form(min_length=1, max_length=30),
    image: UploadFile = File(description="Фото карточки JPG/PNG/WEBP"),
    video: UploadFile = File(description="Короткое видео MP4/MOV/WEBM"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if await repo.get_draft(db, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "У пользователя уже есть черновик")

    image_data, image_type, image_ext = await minio_storage.read_validated(image, "image")
    video_data, video_type, video_ext = await minio_storage.read_validated(video, "video")

    image_url = await minio_storage.upload(image_data, image_type, image_ext, "months/images")
    video_url = await minio_storage.upload(video_data, video_type, video_ext, "months/videos")
    try:
        draft = await repo.create_draft(db, user.id, title.strip(), image_url, video_url)
    except Exception:
        # В БД не сохранилось — убираем уже загруженные файлы, чтобы не копить мусор
        await minio_storage.remove(image_url)
        await minio_storage.remove(video_url)
        raise
    return ApiResponse(data=MonthOut.model_validate(draft), message="Черновик создан")


# 5. PUT публикация: только свой черновик, только draft → published
@router.put("/{month_id}/publish", response_model=ApiResponse[MonthOut])
async def publish_month(
    month_id: int,
    body: MonthPublishIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    month = await repo.get_not_deleted(db, month_id)
    if month is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Месяц не найден")
    if month.creator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Публиковать можно только свои месяцы")
    if month.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Опубликовать можно только черновик")
    month = await repo.publish(db, month, body.model_dump(exclude_none=True))
    return ApiResponse(data=MonthOut.model_validate(month), message="Месяц опубликован")


# 6. DELETE мягкое удаление: только свои месяцы
@router.delete("/{month_id}", response_model=ApiResponse[None])
async def delete_month(
    month_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    month = await repo.get_not_deleted(db, month_id)
    if month is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Месяц не найден")
    if month.creator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Удалять можно только свои месяцы")
    await repo.soft_delete(db, month)
    return ApiResponse(message="Месяц удалён")


# 7. POST лайк от текущего пользователя: value=1 ставит, value=0 снимает
@router.post("/{month_id}/like", response_model=ApiResponse[LikeOut])
async def like_month(
    month_id: int,
    body: LikeIn,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    month = await repo.get_not_deleted(db, month_id)
    if month is None or month.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Месяц не найден")
    is_liked, likes_count = await repo.set_like(db, user.id, month_id, body.value)
    return ApiResponse(data=LikeOut(month_id=month_id, is_liked=is_liked, likes_count=likes_count))
