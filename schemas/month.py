from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from services.storage import media_url

class MonthListItem(BaseModel):
    id: int
    title: str
    norm_temp: int | None
    norm_precip: int | None
    image_url: str
    likes_count: int
    is_mine: int
    
    @field_serializer("image_url")
    def full_url(self, name: str) -> str:
        return media_url(name)
    
class MonthFeedItem(BaseModel):
    
    id: int
    title: str
    norm_temp: int | None
    norm_precip: int | None
    description: str | None
    image_url: str
    video_url: str
    likes_count: int
    is_liked: int
    
    @field_serializer("image_url", "video_url")
    def full_url(self, name: str) -> str:
        return media_url(name)
    
class MonthDraft(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    image_url: str
    video_url: str
    description: str | None
    norm_temp: int | None
    norm_precip: int | None
    
    @field_serializer("image_url", "video_url")
    def full_url(self, name: str) -> str:
        return media_url(name)

class MonthPublish(BaseModel):
    """Что клиент присылает при публикации. Системные поля сюда не входят."""
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=1000)
    norm_temp: int = Field(ge=-50, le=50)
    norm_precip: int = Field(ge=0, le=1000)


class MonthLikeIn(BaseModel):
    """Что клиент присылает при лайке: 1 — поставить, 0 — снять."""
    model_config = ConfigDict(extra="forbid")

    value: Literal[0, 1]


class MonthLikeResult(BaseModel):
    """Ответ на лайк: сколько лайков у месяца и стоит ли лайк текущего пользователя."""
    month_id: int
    likes_count: int
    is_liked: int
