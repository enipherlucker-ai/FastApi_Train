from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User
from app.repositories import UserRepository

# «Сессия из Depends» — записываем один раз и дальше пишем просто SessionDep.
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


async def get_user_or_404(user_id: int, users: UserRepoDep) -> User:
    user = await users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Пользователь из пути /users/{user_id}; если его нет — сразу ответ 404.
UserDep = Annotated[User, Depends(get_user_or_404)]
