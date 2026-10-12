from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import CheckReceiptSettings
from app.database import get_session
from app.models import User
from app.repositories import UserRepository, ApiLogsRepository
from app.config import get_settings
from app.foreign_api.check_receipt import CheckReceipt

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

UserDep = Annotated[UserRepository, Depends(get_user_or_404)]


def get_logs_repository(session: SessionDep) -> ApiLogsRepository:
    return ApiLogsRepository(session)

ApiLogsDep = Annotated[ApiLogsRepository, Depends(get_logs_repository)]

def get_check_receipt_api() -> CheckReceipt:
    return CheckReceipt(
        api_token=settings.check_receipt_token.token,
        url=settings.check_receipt_token.url,
        timeout=settings.check_receipt_token.timeout,
    )

ApiCheckReceiptDep = Annotated[CheckReceipt, Depends(get_check_receipt_api)]
