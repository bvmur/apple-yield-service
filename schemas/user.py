from pydantic import BaseModel, ConfigDict, Field


class UserRegister(BaseModel):
    """Что присылает клиент при регистрации."""
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=30, description="Логин", examples=["nikita_sad"])
    password: str = Field(min_length=6, max_length=100, description="Пароль", examples=["secret123"])

class UserLogin(BaseModel):
    """Что присылает клиент при входе."""
    model_config = ConfigDict(extra="forbid")

    username: str = Field(description="Логин", examples=["nikita_sad"])
    password: str = Field(description="Пароль", examples=["secret123"])

class UserOut(BaseModel):
    """Пользователь в ответе. Пароля здесь нет — и не должно быть."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    
