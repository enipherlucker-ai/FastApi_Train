from collections.abc import Sequence

from sqlalchemy import select

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def find_by_name(self, name: str) -> Sequence[User]:
        stmt = select(User).where(User.name.ilike(f"%{name}%")).order_by(User.id)
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_by_login(self, login: str) -> User | None:
        stmt = select(User).where(User.login == login)
        return await self.session.scalar(stmt)