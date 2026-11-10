import mimetypes
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from minio import Minio
from starlette.concurrency import run_in_threadpool

from core.config import settings

# Один клиент MinIO на всё приложение
client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,            # MinIO у нас без HTTPS
)


def media_url(name: str) -> str:
    """Имя файла из БД → полный адрес, по которому клиент откроет файл."""
    return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{name}"


async def upload(file: UploadFile, kind: str) -> str:
    """Проверить тип, придумать латинское имя, положить файл в MinIO. Вернуть имя."""
    # Некоторые клиенты (в т.ч. Postman) присылают тип "application/octet-stream" —
    # тогда определяем тип по расширению имени файла
    content_type = file.content_type or ""
    if content_type in ("", "application/octet-stream"):
        content_type = mimetypes.guess_type(file.filename or "")[0] or ""

    if not content_type.startswith(f"{kind}/"):
        raise HTTPException(status_code=400, detail=f"Ожидается файл {kind}")

    extension = Path(file.filename or "").suffix.lower()      # ".jpg", ".mp4"
    name = f"{uuid.uuid4().hex}{extension}"                    # "3f9a1c...e2.jpg"

    data = await file.read()
    await run_in_threadpool(
        client.put_object,
        settings.MINIO_BUCKET,
        name,
        BytesIO(data),
        len(data),
        content_type=content_type,
    )
    return name
