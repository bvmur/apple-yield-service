from pydantic import BaseModel


class MonthListItem(BaseModel):
    id: int
    title: str
    norm_temp: int | None
    norm_precip: int | None
    image_url: str
    likes_count: int
    is_mine: int
    
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
    