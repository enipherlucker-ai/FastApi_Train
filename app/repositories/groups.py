from sqlalchemy import select
from collections.abc import Sequence

from app.models import Group
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    model = Group

    async def get_by_name(self, name: str) -> Group | None:
        stmt = select(self.model).where(self.model.name == name)
        return await self.session.scalar(stmt)

    async def list_for_user(self, user_id: int) -> Sequence[Group]:
        stmt = select(self.model).where(self.model.user_id == user_id).order_by(self.model.id)
        result = await self.session.scalars(stmt)
        return result.all()