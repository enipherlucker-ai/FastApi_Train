from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response

from app.api.dependencies import CurrentUserDep, SessionDep, UserRepoDep, UserSessionRepoDep
from app.config import get_settings
from app.constants import SESSION_COOKIE, SESSION_DAYS
from app.models import User
from app.schemas import LoginIn, RegisterIn, UserRead
from app.security import DUMMY_HASH, hash_password, hash_token, new_session_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: RegisterIn, users: UserRepoDep, session: SessionDep) -> User:
    if await users.get_by_login(data.login) is not None:
        raise HTTPException(status_code=409, detail="login already taken")
    user = await users.create(
        **data.model_dump(exclude={"password"}),
        password_hash=hash_password(data.password)
    )
    await session.commit()
    return user


@router.post("/login", response_model=UserRead)
async def login(
        data: LoginIn,
        response: Response,
        users: UserRepoDep,
        user_session: UserSessionRepoDep,
        session: SessionDep,
) -> User:
    user = await users.get_by_login(data.login)
    stored_hash = user.password_hash if user is not None else DUMMY_HASH
    if not verify_password(data.password, stored_hash) or user is None:
        raise HTTPException(status_code=401, detail="wrong user or password")

    token = new_session_token()
    await user_session.create(
        token_hash=hash_token(token),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    await session.commit()

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "dev",
    )
    return user


@router.post("/logout", status_code=204)
async def logout(
        response: Response,
        user_sessions: UserSessionRepoDep,
        session: SessionDep,
        token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
):
    if token is not None:
        user_session = await user_sessions.get_by_token_hash(hash_token(token))
        if user_session is not None:
            await user_sessions.delete(user_session)
            await session.commit()
    response.delete_cookie(SESSION_COOKIE)

@router.get("/me", response_model=UserRead)
async def me(user: CurrentUserDep) -> User:
    return user
