from typing import Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.database import get_session
from app.models import User
from app.repositories import (
    UserRepository,
    ApiLogsRepository,
    ReceiptRepository,
    ReceiptCompoundRepository,
    GroupRepository,
)
from app.config import get_settings
from app.foreign_api.check_receipt import CheckReceipt
from app.foreign_api.categorizer import ReceiptCategorizer
from app.repositories.user_session import UserSessionRepository
from app.security import hash_token

from app.constants import SESSION_COOKIE

settings = get_settings()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


async def get_user_or_404(user_id: int, users: UserRepoDep) -> User:
    user = await users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


UserDep = Annotated[User, Depends(get_user_or_404)]


def get_logs_repository(session: SessionDep) -> ApiLogsRepository:
    return ApiLogsRepository(session)


ApiLogsDep = Annotated[ApiLogsRepository, Depends(get_logs_repository)]


def get_check_receipt_api() -> CheckReceipt:
    return CheckReceipt(
        api_token=settings.check_receipt_settings.token,
        url=settings.check_receipt_settings.url,
        timeout=settings.check_receipt_settings.timeout,
    )


ApiCheckReceiptDep = Annotated[CheckReceipt, Depends(get_check_receipt_api)]


def get_receipt_repository(session: SessionDep) -> ReceiptRepository:
    return ReceiptRepository(session)


ReceiptDep = Annotated[ReceiptRepository, Depends(get_receipt_repository)]


def get_receipt_compound_repository(session: SessionDep) -> ReceiptCompoundRepository:
    return ReceiptCompoundRepository(session)


ReceiptCompoundDep = Annotated[ReceiptCompoundRepository, Depends(get_receipt_compound_repository)]


def get_group_repository(session: SessionDep) -> GroupRepository:
    return GroupRepository(session)


GroupRepoDep = Annotated[GroupRepository, Depends(get_group_repository)]


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.open_ai_settings.api_key,
        base_url=settings.open_ai_settings.base_url,
        timeout=settings.open_ai_settings.timeout,
        max_retries=1,
    )


def get_categorizer() -> ReceiptCategorizer | None:
    if not settings.open_ai_settings.api_key:
        return None
    return ReceiptCategorizer(client=get_openai_client(), model=settings.open_ai_settings.model)


CategorizerDep = Annotated[ReceiptCategorizer | None, Depends(get_categorizer)]


def get_user_session_repository(session: SessionDep) -> UserSessionRepository:
    return UserSessionRepository(session)


UserSessionRepoDep = Annotated[UserSessionRepository, Depends(get_user_session_repository)]


async def get_current_user(
        users: UserRepoDep,
        user_sessions: UserSessionRepoDep,
        token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None
) -> User:
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_session = await user_sessions.get_active(hash_token(token))
    if user_session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await users.get(user_session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
