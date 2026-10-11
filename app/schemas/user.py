from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Типы полей с правилами проверки. Пишутся один раз, используются во всех схемах.
UserName = Annotated[str, Field(min_length=1, max_length=100, examples=["Anna"])]
UserAge = Annotated[int, Field(ge=0, le=150, examples=[30])]
UserDescription = Annotated[str | None, Field(max_length=500, examples=["Любит котов"])]


class UserBase(BaseModel):
    name: UserName
    age: UserAge
    description: UserDescription = None


class UserCreate(UserBase):
    """Что клиент присылает, чтобы создать пользователя."""


class UserUpdate(UserBase):
    """Что клиент присылает, чтобы заменить данные пользователя (PUT)."""


class UserRead(UserBase):
    """Что API отдаёт клиенту."""

    # Разрешить собирать схему из атрибутов ORM-объекта: UserRead.model_validate(user).
    model_config = ConfigDict(from_attributes=True)

    id: int
