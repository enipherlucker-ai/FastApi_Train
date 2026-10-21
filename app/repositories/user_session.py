from datetime import datetime, timezone

from sqlalchemy import select

from app.models import UserSession
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession

    async def get_active(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        return await self.session.scalar(stmt)

    async def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.token_hash == token_hash)
        return await self.session.scalar(stmt)