from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import SessionDep, UserDep, UserRepoDep, ApiLogsDep
from app.constants import ADMIN_USER_ID
from app.models import User
from app.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(tags=["users"])


@router.post("/create_user", response_model=UserRead, status_code=201)
async def create_user(
        data: UserCreate,
        users: UserRepoDep,
        session: SessionDep,
        logs: ApiLogsDep,
) -> User:
    user = await users.create(**data.model_dump())
    await logs.logs_add(
        user_id=ADMIN_USER_ID,
        service="self",
        method="[POST]/create_user",
        comment="Добавление пользователя",
        input_data=str(data),
        output_data=str(user))
    await session.commit()
    return user


@router.get("/users/{user_id}", response_model=UserRead)
async def read_user(user: UserDep) -> User:
    return user


@router.get("/users", response_model=list[UserRead])
async def read_users(
        users: UserRepoDep,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    return list(await users.list(limit=limit, offset=offset))


@router.delete("/users/delete/{user_id}", response_model=UserRead)
async def delete_user(user: UserDep, users: UserRepoDep, session: SessionDep) -> User:
    await users.delete(user)
    await session.commit()
    return user


@router.put("/users/update/{user_id}", response_model=UserRead)
async def update_user(
        user: UserDep,
        data: Annotated[UserUpdate, Query()],
        users: UserRepoDep,
        session: SessionDep,
) -> User:
    await users.update(user, **data.model_dump())
    await session.commit()
    return user
