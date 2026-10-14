"""Работа с MinIO: загрузка фото/видео месяцев и удаление при откате."""
import io
import json
import uuid
from functools import lru_cache

from fastapi import HTTPException, UploadFile
from minio import Minio
from starlette.concurrency import run_in_threadpool

from core.config import settings

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VIDEO_TYPES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024      # 5 МБ
MAX_VIDEO_SIZE = 30 * 1024 * 1024     # 30 МБ — «короткое видео»


@lru_cache(maxsize=1)
def get_minio() -> Minio:
    """Клиент MinIO — один на всё приложение. При первом вызове создаёт бакет
    и разрешает публичное чтение, чтобы фото/видео открывались по ссылке."""
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,  # локально без HTTPS
    )
    bucket = settings.MINIO_BUCKET
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"],
        }],
    }
    client.set_bucket_policy(bucket, json.dumps(policy))
    return client


async def read_validated(file: UploadFile, kind: str) -> tuple[bytes, str, str]:
    """Проверяет тип и размер файла. Возвращает (данные, content_type, расширение)."""
    allowed, max_size, label = (
        (IMAGE_TYPES, MAX_IMAGE_SIZE, "изображением JPG/PNG/WEBP")
        if kind == "image" else
        (VIDEO_TYPES, MAX_VIDEO_SIZE, "видео MP4/MOV/WEBM")
    )
    if file is None or not file.filename:
        raise HTTPException(400, f"Не передан файл ({kind})")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, f"Файл {file.filename} пустой")
    if len(data) > max_size:
        raise HTTPException(400, f"Файл {file.filename} больше {max_size // (1024 * 1024)} МБ")
    # Тип определяем по содержимому файла (первым байтам), а не по заголовку от клиента:
    # клиент (Postman, браузер) может прислать неверный Content-Type или application/octet-stream
    content_type = detect_content_type(data)
    if content_type not in allowed:
        raise HTTPException(400, f"Файл {file.filename} должен быть {label}")
    return data, content_type, allowed[content_type]


def detect_content_type(data: bytes) -> str | None:
    """Определяет тип файла по «магическим» байтам в начале файла."""
    head = data[:16]
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:8] == b"ftyp":
        return "video/quicktime" if head[8:10] == b"qt" else "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return None


async def upload(data: bytes, content_type: str, ext: str, folder: str) -> str:
    """Кладёт файл в MinIO под новым латинским именем (uuid) и возвращает публичную ссылку."""
    object_name = f"{folder}/{uuid.uuid4().hex}{ext}"
    client = await run_in_threadpool(get_minio)
    await run_in_threadpool(
        client.put_object, settings.MINIO_BUCKET, object_name,
        io.BytesIO(data), len(data), content_type=content_type,
    )
    return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{object_name}"


async def remove(url: str | None) -> None:
    """Удаляет объект по ссылке (используется, если запись в БД не сохранилась)."""
    prefix = f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/"
    if url and url.startswith(prefix):
        client = await run_in_threadpool(get_minio)
        await run_in_threadpool(client.remove_object, settings.MINIO_BUCKET, url[len(prefix):])
