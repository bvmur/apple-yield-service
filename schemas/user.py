from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    """Что присылает клиент при регистрации."""
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=100)


class UserOut(BaseModel):
    """Пользователь в ответе. Пароля здесь нет — и не должно быть."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str