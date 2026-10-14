from pydantic import BaseModel, ConfigDict, Field


class UserRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=128)


class UserLoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    """Пароль (хэш) наружу никогда не отдаём — его просто нет в схеме."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_moderator: bool
