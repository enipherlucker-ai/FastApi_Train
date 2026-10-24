from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.user import UserBase

Login = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$", examples=["anna"])]
Password = Annotated[str, Field(min_length=8, max_length=128, examples=["correct-horse-42"])]


class RegisterIn(UserBase):
    login: Login
    password: Password


class LoginIn(BaseModel):
    login: Login
    password: Password